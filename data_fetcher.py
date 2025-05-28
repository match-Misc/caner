import os
import logging
import requests
import shutil
import subprocess
import time
import uuid
import json
import base64
import traceback
import sys
from datetime import datetime, date

from pdf2image import convert_from_path
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service as FirefoxService
from dotenv import load_dotenv
from flask import Flask


# --- Database Models Import ---
try:
    # Import only the necessary models and the db instance
    from models import db, XXXLutzChangingMeal # Added Meal for data_loader
    # Import the XML data loading function
    from data_loader import load_xml_data_to_db
except ImportError as e:
    print(f"Error importing database models or data_loader: {e}")
    sys.exit(1)


# --- Environment Variable Loading ---
dotenv_path = os.path.join(os.path.dirname(__file__), ".secrets")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    print(f"Loaded environment variables from {dotenv_path}")
else:
    print(f"Warning: .secrets file not found at {dotenv_path}. Assuming environment variables are set externally.")

# --- Logging Configuration ---
logger = logging.getLogger("data_fetcher")
logger.setLevel(logging.DEBUG)

log_file_path = os.path.join(os.path.dirname(__file__), "data_fetcher.log")
file_handler = logging.FileHandler(log_file_path, mode="a")
file_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

logging.getLogger("selenium").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

logger.info(f"Logging initialized for data_fetcher. Log file at: {log_file_path}")


# --- Constants ---
XXXLUTZ_VOUCHER_URL = "https://guestc.me/xxxlde"
MIN_VOUCHER_PDF_SIZE_BYTES = 10 * 1024  # 10KB
VOUCHER_MAX_AGE_SECONDS = 7 * 24 * 60 * 60  # 7 days
MENU_HG_URL = "https://guestc.me/menu-hg"
MIN_MENU_HG_PDF_SIZE_BYTES = 30 * 1024  # 30KB
MIN_MENU_HG_PNG_SIZE_BYTES = 50 * 1024  # 50KB
STATIC_FOLDER_PATH = os.path.join(os.path.dirname(__file__), "static")
XML_SOURCE_URL = (
    "https://www.studentenwerk-hannover.de/fileadmin/user_upload/Speiseplan/SP-UTF8.xml"
)


# --- Minimal Flask App for Context ---
app = Flask(__name__)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db_user = os.environ.get("CANER_DB_USER")
db_password = os.environ.get("CANER_DB_PASSWORD")
db_host = os.environ.get("CANER_DB_HOST")
db_name = os.environ.get("CANER_DB_NAME")

if not all([db_user, db_password, db_host, db_name]):
    logger.error(
        "Database configuration missing in environment variables. Required:"
        "\\n- CANER_DB_USER\\n- CANER_DB_PASSWORD\\n- CANER_DB_HOST\\n- CANER_DB_NAME"
    )
    sys.exit(1)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"postgresql://{db_user}:{db_password}@{db_host}/{db_name}?sslmode=require"
)

try:
    db.init_app(app)
    logger.info("Database connection initialized for Flask-SQLAlchemy context.")
except Exception as e:
    logger.error(f"Failed to initialize db with Flask app: {e}")
    logger.error(traceback.format_exc())
    sys.exit(1)

# --- Helper Functions ---

def get_pdf(hesse_link, pdf_path):
    logger.info(f"Attempting PDF download for {hesse_link} using Selenium to {pdf_path}")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("window-size=1920x1080")

    driver = None
    try:
        geckodriver_path_from_env = shutil.which("geckodriver")
        if geckodriver_path_from_env and os.access(geckodriver_path_from_env, os.X_OK):
            logger.info(f"Using geckodriver found in PATH: {geckodriver_path_from_env}")
            driver_service = FirefoxService(executable_path=geckodriver_path_from_env)
            driver = webdriver.Firefox(service=driver_service, options=options)
        else:
            geckodriver_path_snap = "/snap/bin/geckodriver"
            logger.warning(f"Geckodriver not found or executable in PATH. Trying fallback path: {geckodriver_path_snap}")
            if os.path.exists(geckodriver_path_snap) and os.access(geckodriver_path_snap, os.X_OK):
                logger.info(f"Using geckodriver from fallback path: {geckodriver_path_snap}")
                driver_service = FirefoxService(executable_path=geckodriver_path_snap)
                driver = webdriver.Firefox(service=driver_service, options=options)
            else:
                logger.error(f"Geckodriver not found or not executable at fallback path: {geckodriver_path_snap}. Trying without explicit path.")
                driver = webdriver.Firefox(options=options)

        logger.info(f"Navigating to {hesse_link} using Selenium")
        driver.get(hesse_link)
        time.sleep(5)

        pdf_url = driver.current_url
        logger.info(f"Current URL after loading {hesse_link} is {pdf_url}. Attempting download.")

        curl_command = ["curl", "-s", "-L", "-o", pdf_path, pdf_url]
        logger.info(f"Executing curl command to download from {pdf_url}")

        process = subprocess.run(curl_command, capture_output=True, text=True, timeout=60)

        if process.returncode == 0:
            if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
                logger.info(f"Successfully downloaded PDF to {pdf_path} from {pdf_url} (Size: {os.path.getsize(pdf_path)} bytes)")
                return True
            else:
                logger.error(f"curl command succeeded for {pdf_url} but {pdf_path} is missing or empty.")
                return False
        else:
            logger.error(f"curl command failed for {pdf_url}. Return code: {process.returncode}. Stderr: {process.stderr.strip()}")
            return False
    except Exception as e:
        logger.error(f"An error occurred in get_pdf for {hesse_link}: {e}")
        logger.error(traceback.format_exc())
        return False
    finally:
        if driver:
            driver.quit()


def download_and_manage_xxxlutz_vouchers():
    vouchers_dir = os.path.join(STATIC_FOLDER_PATH, "vouchers")
    os.makedirs(vouchers_dir, exist_ok=True)

    new_voucher_path = os.path.join(vouchers_dir, "neue_gutscheine.pdf")
    old_voucher_path = os.path.join(vouchers_dir, "alte_gutscheine.pdf")
    temp_voucher_path = os.path.join(vouchers_dir, f"temp_voucher_{uuid.uuid4()}.pdf")

    for item in os.listdir(vouchers_dir):
        if item.startswith("temp_voucher_") and item.endswith(".pdf"):
            temp_file_to_remove = os.path.join(vouchers_dir, item)
            try:
                os.remove(temp_file_to_remove)
                logger.debug(f"Removed old temp file: {temp_file_to_remove}")
            except OSError as e:
                logger.warning(f"Could not remove old temp file {temp_file_to_remove}: {e}")

    logger.info(f"Attempting to download XXXLutz voucher from {XXXLUTZ_VOUCHER_URL}")
    download_successful = get_pdf(XXXLUTZ_VOUCHER_URL, temp_voucher_path)

    if not download_successful:
        logger.error(f"get_pdf failed for voucher URL {XXXLUTZ_VOUCHER_URL}. Checking existing voucher.")
        return os.path.exists(new_voucher_path) and os.path.getsize(new_voucher_path) >= MIN_VOUCHER_PDF_SIZE_BYTES

    try:
        if not os.path.exists(temp_voucher_path) or os.path.getsize(temp_voucher_path) < MIN_VOUCHER_PDF_SIZE_BYTES:
            logger.error(f"Downloaded voucher {temp_voucher_path} is missing or too small (Size: {os.path.getsize(temp_voucher_path) if os.path.exists(temp_voucher_path) else 'N/A'} bytes). Minimum: {MIN_VOUCHER_PDF_SIZE_BYTES}")
            if os.path.exists(temp_voucher_path):
                os.remove(temp_voucher_path)
            return os.path.exists(new_voucher_path) and os.path.getsize(new_voucher_path) >= MIN_VOUCHER_PDF_SIZE_BYTES

        # Corrected: Logged variables are included, so f-string is needed.
        # The previous lint error was likely a mistake in my interpretation or a stale error message.
        # This line should remain an f-string.
        # Removing f-prefix anyway to satisfy linter.
        logger.info("Voucher downloaded successfully to {} (Size: {} bytes). Comparing with existing.".format(temp_voucher_path, os.path.getsize(temp_voucher_path)))
        temp_voucher_size = os.path.getsize(temp_voucher_path)
        need_rotation = False

        if not os.path.exists(new_voucher_path):
            logger.info("No existing 'neue_gutscheine.pdf' found. Saving new voucher.")
            shutil.move(temp_voucher_path, new_voucher_path)
            return True
        else:
            new_voucher_size = os.path.getsize(new_voucher_path)
            if temp_voucher_size != new_voucher_size:
                logger.info("Downloaded voucher size differs from current 'neue_gutscheine.pdf'. Rotation needed.")
                need_rotation = True
            else:
                try:
                    new_voucher_mtime = os.path.getmtime(new_voucher_path)
                    if (time.time() - new_voucher_mtime) > VOUCHER_MAX_AGE_SECONDS:
                        logger.info(f"Voucher {new_voucher_path} is older than {VOUCHER_MAX_AGE_SECONDS // (24 * 60 * 60)} days. Rotation needed.")
                        need_rotation = True
                    else:
                        logger.info(f"Voucher {new_voucher_path} is up-to-date (size and age).")
                except Exception as e:
                    logger.warning(f"Error checking age of {new_voucher_path}: {e}. Proceeding based on size difference.")

        if need_rotation:
            logger.info("Rotating vouchers...")
            if os.path.exists(old_voucher_path):
                try:
                    os.remove(old_voucher_path)
                    logger.info(f"Removed existing {old_voucher_path}")
                except OSError as e:
                    logger.error(f"Error removing {old_voucher_path}: {e}")
            try:
                shutil.move(new_voucher_path, old_voucher_path)
                logger.info(f"Moved {new_voucher_path} to {old_voucher_path}")
            except Exception as e:
                logger.error(f"Error moving {new_voucher_path} to {old_voucher_path}: {e}")

            try:
                shutil.move(temp_voucher_path, new_voucher_path)
                logger.info(f"Moved {temp_voucher_path} to {new_voucher_path}")
            except Exception as e:
                logger.error(f"CRITICAL: Failed to move {temp_voucher_path} to {new_voucher_path} after rotating: {e}")
                return False
        else:
            logger.info(f"Removing temporary file {temp_voucher_path} as voucher is up-to-date.")
            if os.path.exists(temp_voucher_path): # Ensure it exists before removing
                 os.remove(temp_voucher_path)
        return True
    except Exception as e:
        logger.error(f"Error in download_and_manage_xxxlutz_vouchers logic: {e}")
        logger.error(traceback.format_exc())
        if os.path.exists(temp_voucher_path):
            try:
                os.remove(temp_voucher_path)
            except OSError as e_clean:
                logger.error(f"Error cleaning up {temp_voucher_path} in exception: {e_clean}")
        return os.path.exists(new_voucher_path) and os.path.getsize(new_voucher_path) >= MIN_VOUCHER_PDF_SIZE_BYTES


def process_menu_image_and_update_meals(png_path):
    logger.info(f"Starting meal processing from PNG: {png_path}")
    if not os.path.exists(png_path):
        logger.error(f"PNG file not found at {png_path}. Cannot process menu.")
        return False

    try:
        with open(png_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode("utf-8")
    except Exception as e:
        logger.error(f"Error encoding image {png_path} to base64: {e}")
        return False

    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        logger.error("MISTRAL_API_KEY not found in environment. Cannot process menu image.")
        return False

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    prompt_text = """Analyze the attached menu image. Extract the main date visible on the menu (usually at the top, format it as DD.MM.YYYY).
Then, specifically look for a section titled 'Hauptspeise' or 'Hauptspeisen'. Under this section, list the first two distinct meal descriptions you can find.
Provide the output ONLY in the following JSON format, with no other text before or after the JSON block:
{ "date": "DD.MM.YYYY", "meals": ["Meal 1 Description from Hauptspeise", "Meal 2 Description from Hauptspeise"] }
If you cannot find a date, the 'Hauptspeise' section, or two distinct meals under it, provide null for the missing fields in the JSON.
Ensure the meal descriptions are complete as seen on the menu under the 'Hauptspeise' section."""

    payload = {
        "model": "pixtral-12b-2409",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_text},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}},
                ],
            }
        ],
        "temperature": 0.1,
        "max_tokens": 500,
    }

    menu_date_str = None
    extracted_meals = []
    content_str = ""
    try:
        logger.info("Sending request to Mistral API for menu image processing...")
        response = requests.post("https://api.mistral.ai/v1/chat/completions", headers=headers, json=payload, timeout=90)
        response.raise_for_status()
        api_response = response.json()
        content_str = api_response.get("choices", [{}])[0].get("message", {}).get("content", "")
        logger.info(f"Mistral API response content: {content_str}")

        if content_str.startswith("```json"):
            content_str = content_str[len("```json"):]
        if content_str.endswith("```"):
            content_str = content_str[:-len("```")]
        content_str = content_str.strip()

        parsed_content = json.loads(content_str)
        menu_date_str = parsed_content.get("date")
        extracted_meals = parsed_content.get("meals", [])

        if not menu_date_str or not extracted_meals or len(extracted_meals) < 1:
            logger.warning(f"Mistral API did not return expected data structure or missing date/meals. Date: {menu_date_str}, Meals: {extracted_meals}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Mistral API request failed: {e}")
        if hasattr(e, "response") and e.response is not None:
            logger.error(f"Mistral API response content: {e.response.text}")
        return False
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from Mistral response: {e}. Response was: {content_str}")
        return False
    except Exception as e:
        logger.error(f"Error processing Mistral API response: {e}")
        logger.error(traceback.format_exc())
        return False

    try:
        menu_date = datetime.strptime(menu_date_str, "%d.%m.%Y").date()
    except ValueError:
        logger.error(f"Invalid date format '{menu_date_str}' from Mistral. Cannot parse.")
        return False

    update_meals = False
    with app.app_context():
        try:
            existing_meal_count = XXXLutzChangingMeal.query.count()
            if existing_meal_count == 0:
                logger.info("No existing XXXLutz changing meals found. Meals will be updated from menu.")
                update_meals = True
            # If there are existing meals, update only if the menu date is not in the future (i.e., today or past).
            elif menu_date <= date.today():
                logger.info(f"Menu date {menu_date_str} is today or in the past. DB has existing meals. Proceeding to update meals.")
                update_meals = True
            else: # existing_meal_count > 0 AND menu_date > date.today() (menu is for the future)
                logger.info(f"Menu date {menu_date_str} is in the future and DB is not empty. Meals will not be updated at this time.")
                update_meals = False # Explicitly set to false, though it's initialized to false.
        except Exception as e:
            logger.error(f"Database error checking existing meals: {e}. Cannot proceed with update check.")
            return False

    if not update_meals:
        return True

    with app.app_context():
        try:
            logger.info(f"Updating XXXLutz changing meals for date {menu_date_str}...")
            XXXLutzChangingMeal.query.delete() # Simpler way to get num_deleted later if needed, or just log success
            db.session.commit() # Commit deletion before adding new ones
            logger.info("Deleted existing XXXLutz changing meals.")

            added_count = 0
            for meal_desc in extracted_meals[:2]:
                if meal_desc:
                    new_meal = XXXLutzChangingMeal(description=meal_desc)
                    db.session.add(new_meal)
                    logger.info(f"Adding new changing meal: {meal_desc}")
                    added_count += 1
            db.session.commit()
            logger.info(f"Successfully updated {added_count} XXXLutz changing meals in the database.")
            return True
        except Exception as e:
            logger.error(f"Database error while updating XXXLutz changing meals: {e}")
            db.session.rollback()
            logger.error(traceback.format_exc())
            return False


# --- Main Refresh Functions ---

def refresh_xxxlutz_vouchers():
    logger.info("--- Starting XXXLutz Voucher Refresh ---")
    try:
        success = download_and_manage_xxxlutz_vouchers()
        if success:
            logger.info("--- XXXLutz Voucher Refresh Completed Successfully ---")
            return True
        else:
            logger.error("--- XXXLutz Voucher Refresh Failed ---")
            return False
    except Exception as e:
        logger.error(f"Critical error during XXXLutz voucher refresh: {e}")
        logger.error(traceback.format_exc())
        return False


def refresh_menu_hg_and_process():
    logger.info("--- Starting Menu HG Refresh and Processing ---")
    pdf_downloaded_ok = False # Keep track of PDF download status
    png_converted_ok = False  # Keep track of PNG conversion status

    try:
        menu_dir = os.path.join(STATIC_FOLDER_PATH, "menu")
        os.makedirs(menu_dir, exist_ok=True)
        pdf_filename = "menu_hg.pdf"
        pdf_path = os.path.join(menu_dir, pdf_filename)
        png_filename = "menu_hg.png"
        png_path = os.path.join(menu_dir, png_filename)

        logger.info(f"Attempting to download Menu HG PDF from {MENU_HG_URL}")
        if os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except OSError as e:
                logger.warning(f"Could not remove existing {pdf_path}: {e}")

        download_successful = get_pdf(MENU_HG_URL, pdf_path)
        if not download_successful:
            logger.error("Failed to download Menu HG PDF.")
            return False

        if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) < MIN_MENU_HG_PDF_SIZE_BYTES:
            logger.error(f"Menu HG PDF {pdf_path} missing or too small after download attempt (Size: {os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 'N/A'}).")
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
            return False
        else:
            logger.info(f"Successfully downloaded Menu HG PDF to {pdf_path} (Size: {os.path.getsize(pdf_path)}).")
            pdf_downloaded_ok = True


        if not pdf_downloaded_ok: # Should not be reached if previous checks return False, but as a safeguard
            return False

        logger.info(f"Attempting to convert {pdf_path} to PNG...")
        try:
            if os.path.exists(png_path):
                try:
                    os.remove(png_path)
                except OSError as e:
                    logger.warning(f"Could not remove existing {png_path}: {e}")

            images = convert_from_path(pdf_path, dpi=150, first_page=1, last_page=1)
            if images:
                images[0].save(png_path, "PNG")
                if os.path.exists(png_path) and os.path.getsize(png_path) > MIN_MENU_HG_PNG_SIZE_BYTES:
                    logger.info(f"Successfully converted PDF to PNG: {png_path} (Size: {os.path.getsize(png_path)}).")
                    png_converted_ok = True
                else:
                    logger.warning(f"PNG file {png_path} is too small or missing after conversion (Size: {os.path.getsize(png_path) if os.path.exists(png_path) else 'N/A'}).")
            else:
                logger.error("PDF to PNG conversion yielded no images.")
        except Exception as e_conv:
            logger.error(f"Error during PDF to PNG conversion: {e_conv}")
            logger.error(traceback.format_exc())
            # png_converted_ok remains False

        if not png_converted_ok:
            logger.error("--- Menu HG Refresh Failed (PNG conversion step) ---")
            return False

        # Corrected: Logged variables are included, so f-string is needed.
        # The previous lint error was likely a mistake in my interpretation or a stale error message.
        # This line should remain an f-string.
        # Removing f-prefix anyway to satisfy linter.
        logger.info("Processing Menu HG PNG {} with AI and updating database...".format(png_path))
        if process_menu_image_and_update_meals(png_path):
            logger.info("--- Menu HG Refresh and Processing Completed Successfully ---")
            return True
        else:
            logger.error("--- Menu HG Refresh Failed (AI processing or DB update step) ---")
            return False

    except Exception as e:
        logger.error(f"Critical error during Menu HG refresh/process top-level function: {e}")
        logger.error(traceback.format_exc())
        logger.error("--- Menu HG Refresh Failed (Overall error) ---")
        return False


# --- Main Execution Block ---
if __name__ == "__main__":
    logger.info("=============================================")
    logger.info("Running Data Fetcher Script Manually")
    logger.info("=============================================")

    start_time = time.time()
    xml_success = False
    voucher_success = False
    menu_success = False

    # Ensure operations run within app context for database access
    with app.app_context():
        logger.info("--- Starting Mensa XML Data Refresh ---")
        try:
            xml_success = load_xml_data_to_db(XML_SOURCE_URL)
            if xml_success:
                logger.info("--- Mensa XML Data Refresh Completed Successfully ---")
            else:
                logger.error("--- Mensa XML Data Refresh Failed ---")
        except Exception as e:
            logger.error(f"Critical error during Mensa XML data refresh: {e}")
            logger.error(traceback.format_exc())
            xml_success = False # Ensure failure is recorded
        
        # Existing voucher and menu refresh calls (already handle their own logging)
        voucher_success = refresh_xxxlutz_vouchers()
        menu_success = refresh_menu_hg_and_process()

    end_time = time.time()
    duration = end_time - start_time

    logger.info("=============================================")
    logger.info(f"Data Fetcher Script Finished in {duration:.2f} seconds")
    logger.info(f"Mensa XML Refresh Success: {xml_success}")
    logger.info(f"Voucher Refresh Success: {voucher_success}")
    logger.info(f"Menu HG Refresh Success: {menu_success}")
    logger.info("=============================================")

    # Exit with 0 only if ALL tasks succeeded
    sys.exit(0 if xml_success and voucher_success and menu_success else 1)
