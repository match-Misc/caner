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
import threading  # Added for background tasks
from datetime import datetime, date

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    make_response,
    send_from_directory,
)
from pdf2image import convert_from_path
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service as FirefoxService
from dotenv import load_dotenv

# Application-specific imports
# These must come after all standard and third-party library imports
from utils.xml_parser import parse_mensa_data, get_available_mensen, get_available_dates
from models import db, Meal, XXXLutzChangingMeal, XXXLutzFixedMeal, MealVote, PageView
from data_loader import load_xml_data_to_db, load_xxxlutz_meals

# Load environment variables. This must be done after all imports but before any code that uses env vars.
dotenv_path = os.path.join(os.path.dirname(__file__), ".secrets")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
else:
    # If running in an environment where .secrets might not be present (e.g., Docker, CI),
    # this allows the app to continue if env vars are set externally.
    print(
        f"Warning: .secrets file not found at {dotenv_path}. Ensure environment variables are set."
    )


# Configure logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set a base level for the logger instance

# Create a file handler
log_file_path = os.path.join(os.path.dirname(__file__), "app.log")
file_handler = logging.FileHandler(
    log_file_path, mode="w"
)  # 'w' to overwrite log on each run, use 'a' to append
# Changed level from DEBUG to INFO to reduce log file verbosity
file_handler.setLevel(logging.INFO)

# Create a console handler for higher level messages (optional, but good for quick checks)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)  # Show INFO and above on console

# Create a formatter and set it for both handlers
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(file_handler)
# Add console handler ONLY to the app's logger, not the root logger, to avoid double console logs from propagation.
logger.addHandler(console_handler)

# Set the root logger level. This allows libraries to log if needed,
# but only handlers explicitly added to the root logger (or propagating from children)
# will output them. We only added file_handler to the 'app' logger.
# Libraries logging at DEBUG will now not write to our file unless we change file_handler level.
# Consider WARNING for less noise from libraries if needed.
logging.getLogger().setLevel(logging.INFO)

# Important: Removed logging.getLogger().addHandler(file_handler) to prevent duplicate file logs.
# Important: Removed logger.addHandler(console_handler) from the root logger if it was there. Added above to specific logger.

logger.info(f"Logging initialized. Log file at: {log_file_path}")


# Constants
XXXLUTZ_VOUCHER_URL = "https://guestc.me/xxxlde"  # Placeholder URL
MIN_VOUCHER_PDF_SIZE_BYTES = 10 * 1024  # 10KB for XXXLutz vouchers
VOUCHER_MAX_AGE_SECONDS = 7 * 24 * 60 * 60  # 7 days
XML_SOURCE_URL = (
    "https://www.studentenwerk-hannover.de/fileadmin/user_upload/Speiseplan/SP-UTF8.xml"
)
MENU_HG_URL = "https://guestc.me/menu-hg"
MIN_MENU_HG_PDF_SIZE_BYTES = 30 * 1024  # 30KB
MIN_MENU_HG_PNG_SIZE_BYTES = 50 * 1024  # 50KB

# --- START: Added for periodic data refresh ---
DATA_REFRESH_INTERVAL_SECONDS = 4 * 60 * 60  # 4 hours
last_xml_refresh_time = 0
last_vouchers_refresh_time = 0
last_menu_hg_refresh_time = 0
# --- END: Added for periodic data refresh ---

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key")

# Configure the database
# All database configuration is loaded from .secrets
db_user = os.environ.get("CANER_DB_USER")
db_password = os.environ.get("CANER_DB_PASSWORD")
db_host = os.environ.get("CANER_DB_HOST")
db_name = os.environ.get("CANER_DB_NAME")

if not all([db_user, db_password, db_host, db_name]):
    logger.error(
        "Database configuration missing. Please ensure all database-related environment variables are set in .secrets:"
        "\n- CANER_DB_USER\n- CANER_DB_PASSWORD\n- CANER_DB_HOST\n- CANER_DB_NAME"
    )
    # Potentially exit or raise an error here if the database connection is critical for startup
    # For now, we'll let it try to connect, which will fail informatively.

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"postgresql://{db_user}:{db_password}@{db_host}/{db_name}?sslmode=require"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the database
db.init_app(app)


# --- START: Data Refresh Functions ---


def refresh_mensa_xml_data():
    global mensa_data, available_mensen, available_dates, last_xml_refresh_time
    logger.info("Attempting to refresh Mensa XML data...")
    xml_source = XML_SOURCE_URL
    try:
        with app.app_context():
            load_success = load_xml_data_to_db(xml_source)
            if load_success:
                logger.info(
                    "Successfully loaded XML data into database during refresh."
                )
            else:
                logger.error("Failed to load XML data into database during refresh.")

            current_mensa_data = parse_mensa_data(xml_source)
            current_available_mensen = get_available_mensen(current_mensa_data)
            current_available_dates = get_available_dates(current_mensa_data)

            if (
                current_mensa_data
                and current_available_mensen
                and current_available_dates
            ):
                mensa_data = current_mensa_data
                available_mensen = current_available_mensen
                available_dates = current_available_dates
                logger.info(
                    f"Refreshed in-memory Mensa data: {len(available_mensen)} mensen, {len(available_dates)} dates."
                )
            else:
                logger.warning(
                    "Mensa XML parsing during refresh yielded no/incomplete data. In-memory data not updated."
                )

            last_xml_refresh_time = time.time()
            return True
    except Exception as e:
        logger.error(f"Error during Mensa XML data refresh: {e}")
        logger.error(traceback.format_exc())
        return False


def refresh_xxxlutz_vouchers():
    global last_vouchers_refresh_time
    logger.info("Attempting to refresh XXXLutz vouchers...")
    try:
        with app.app_context():
            success = download_and_manage_xxxlutz_vouchers()
            if success:
                logger.info("Successfully refreshed XXXLutz vouchers.")
                last_vouchers_refresh_time = time.time()
            else:
                logger.error("Failed to refresh XXXLutz vouchers.")
            return success
    except Exception as e:
        logger.error(f"Error during XXXLutz voucher refresh: {e}")
        logger.error(traceback.format_exc())
        return False


def refresh_menu_hg_and_process():
    global last_menu_hg_refresh_time
    logger.info("Attempting to refresh and process Menu HG PDF/PNG...")
    try:
        with app.app_context():
            static_folder = app.static_folder if app.static_folder else "static"
            menu_dir = os.path.join(static_folder, "menu")
            os.makedirs(menu_dir, exist_ok=True)
            pdf_filename = "menu_hg.pdf"
            pdf_path = os.path.join(menu_dir, pdf_filename)
            png_filename = "menu_hg.png"
            png_path = os.path.join(menu_dir, png_filename)

            if os.path.exists(pdf_path):
                try:
                    os.remove(pdf_path)
                except OSError as e:
                    logger.warning(
                        f"Could not remove existing menu_hg.pdf before refresh: {e}"
                    )

            download_successful = get_pdf(MENU_HG_URL, pdf_path)
            if not download_successful:
                logger.error("get_pdf failed for Menu HG PDF during refresh.")
                return False
            if (
                not os.path.exists(pdf_path)
                or os.path.getsize(pdf_path) < MIN_MENU_HG_PDF_SIZE_BYTES
            ):
                logger.error(
                    f"Menu HG PDF at {pdf_path} is missing or too small after download attempt during refresh. Size: {os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 'N/A'}"
                )
                if os.path.exists(pdf_path):
                    try:
                        os.remove(pdf_path)
                    except Exception as e_rm:
                        logger.error(f"Failed to remove small PDF {pdf_path}: {e_rm}")
                return False

            logger.info(
                f"Successfully downloaded new Menu HG PDF to {pdf_path} (Size: {os.path.getsize(pdf_path)}) during refresh."
            )

            conversion_to_png_successful = False
            try:
                images = convert_from_path(pdf_path, dpi=150, first_page=1, last_page=1)
                if images:
                    if os.path.exists(png_path):
                        try:
                            os.remove(png_path)
                        except Exception as e_rm:
                            logger.error(f"Failed to remove old PNG {png_path}: {e_rm}")
                    images[0].save(png_path, "PNG")
                    if (
                        os.path.exists(png_path)
                        and os.path.getsize(png_path) > MIN_MENU_HG_PNG_SIZE_BYTES
                    ):
                        logger.info(
                            f"Successfully converted PDF to PNG: {png_path} (Size: {os.path.getsize(png_path)}) during refresh."
                        )
                        conversion_to_png_successful = True
                    else:
                        logger.warning(
                            f"PNG file {png_path} is too small or missing after conversion during refresh. Size: {os.path.getsize(png_path) if os.path.exists(png_path) else 'N/A'}"
                        )
                else:
                    logger.error(
                        "PDF to PNG conversion yielded no images during refresh."
                    )
            except Exception as e_conv:
                logger.error(
                    f"Error during PDF to PNG conversion for refresh: {e_conv}"
                )
                logger.error(traceback.format_exc())

            if conversion_to_png_successful:
                logger.info(
                    f"Processing Menu HG PNG ({png_path}) with AI during refresh."
                )
                process_menu_image_and_update_meals(png_path)
                last_menu_hg_refresh_time = time.time()
                return True
            else:
                logger.warning(
                    "Skipping AI menu processing during refresh due to PNG conversion failure."
                )
                return False  # Indicate that the full process wasn't successful
    except Exception as e:
        logger.error(f"Error during Menu HG refresh and process: {e}")
        logger.error(traceback.format_exc())
        return False


def perform_all_initial_loads():
    logger.info("Performing initial data loads at application startup...")
    # Ensure app context for operations that might need it directly or indirectly
    # although refresh functions now manage their own contexts.
    with app.app_context():
        refresh_mensa_xml_data()
        refresh_xxxlutz_vouchers()
        refresh_menu_hg_and_process()
    logger.info("Initial data loads completed.")


def background_scheduler():
    logger.info(
        f"Background refresh scheduler started. Update interval: {DATA_REFRESH_INTERVAL_SECONDS / 3600:.1f} hours."
    )
    # Initial sleep to avoid immediate re-run after startup load,
    while True:
        time.sleep(DATA_REFRESH_INTERVAL_SECONDS)
        logger.info(
            "Running scheduled data refresh cycle..."
        )  # Removed unnecessary f-string marker
        # These functions handle their own app_context internally
        refresh_mensa_xml_data()
        refresh_xxxlutz_vouchers()
        refresh_menu_hg_and_process()
        logger.info("Scheduled data refresh cycle completed.")


# --- END: Data Refresh Functions ---


def get_pdf(hesse_link, pdf_path):
    logger.info(
        f"Attempting PDF download for {hesse_link} using Selenium to {pdf_path}"
    )
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")  # Often recommended for headless
    options.add_argument(
        "window-size=1920x1080"
    )  # Can sometimes help with layout issues

    driver = None  # Initialize driver to None for finally block
    try:
        geckodriver_path = "/snap/bin/geckodriver"  # Using user-provided path
        logger.info(f"Using geckodriver path: {geckodriver_path}")
        # Check if the geckodriver path exists and is executable
        if not (
            os.path.exists(geckodriver_path) and os.access(geckodriver_path, os.X_OK)
        ):
            logger.error(
                f"Geckodriver not found or not executable at {geckodriver_path}. Please ensure it's installed correctly and the path is correct."
            )
            # Attempt to use geckodriver from PATH as a fallback
            logger.warning(
                "Attempting to use geckodriver from system PATH as a fallback."
            )
            driver = webdriver.Firefox(options=options)
        else:
            driver_service = FirefoxService(executable_path=geckodriver_path)
            driver = webdriver.Firefox(service=driver_service, options=options)

        logger.info(f"Navigating to {hesse_link} using Selenium") # Changed level to INFO
        driver.get(hesse_link)

        # Wait for the page to load and potentially for JavaScript to execute or redirects to happen.
        # The original code had an explicit time.sleep(5).
        # WebDriverWait can be more precise if there's a specific condition to wait for.
        # For now, keeping the sleep as per the provided snippet.
        # logger.debug(f"Waiting for 5 seconds after navigating to {hesse_link}") # Removed DEBUG log
        time.sleep(5)

        pdf_url = driver.current_url
        logger.info(
            f"Current URL after loading {hesse_link} is {pdf_url}. Attempting download."
        )

        # Use curl to download the PDF. Selenium itself can't directly save arbitrary files easily
        # like this unless it's a known download behavior handled by print-to-PDF or specific profile settings.
        # Using curl for the actual download from the (potentially new) pdf_url is a robust choice.
        curl_command = [
            "curl",
            "-s",
            "-L",
            "-o",
            pdf_path,
            pdf_url,
        ]  # Added -L to follow redirects from pdf_url too
        logger.info(f"Executing curl command to download from {pdf_url}") # Changed level to INFO and simplified message

        process = subprocess.run(
            curl_command, capture_output=True, text=True, timeout=60
        )  # Increased timeout for download

        if process.returncode == 0:
            if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
                logger.info(
                    f"Successfully downloaded PDF to {pdf_path} from {pdf_url} (Size: {os.path.getsize(pdf_path)} bytes)"
                )
                return True
            else:
                logger.error(
                    f"curl command succeeded for {pdf_url} but {pdf_path} is missing or empty."
                )
                return False
        else:
            logger.error(
                f"curl command failed for {pdf_url}. Return code: {process.returncode}. Stderr: {process.stderr.strip()}"
            )
            return False

    except Exception as e:
        logger.error(f"An error occurred in get_pdf for {hesse_link}: {e}")
        # Include stack trace for better debugging
        logger.error(traceback.format_exc())
        return False
    finally:
        if driver:
            # logger.debug("Quitting Selenium WebDriver.") # Removed DEBUG log
            driver.quit()


# Function to download and manage XXXLutz vouchers
def download_and_manage_xxxlutz_vouchers():
    """
    Downloads the XXXLutz voucher PDF using Selenium via get_pdf function from XXXLUTZ_VOUCHER_URL.
    If a new PDF is found (different size from existing one or older than VOUCHER_MAX_AGE_SECONDS),
    it sets the old one as "Alte Gutscheine" and the new one as "Neue Gutscheine".
    """
    static_folder = app.static_folder if app.static_folder else "static"
    vouchers_dir = os.path.join(static_folder, "vouchers")
    os.makedirs(vouchers_dir, exist_ok=True)

    new_voucher_path = os.path.join(vouchers_dir, "neue_gutscheine.pdf")
    old_voucher_path = os.path.join(vouchers_dir, "alte_gutscheine.pdf")
    temp_voucher_path = os.path.join(vouchers_dir, "temp_voucher.pdf")

    if os.path.exists(temp_voucher_path):
        try:
            os.remove(temp_voucher_path)
        except OSError as e:
            logger.error(
                f"Error removing pre-existing temporary voucher file {temp_voucher_path}: {e}"
            )
            pass

    logger.info(
        f"Attempting to download XXXLutz voucher using Selenium/get_pdf from {XXXLUTZ_VOUCHER_URL}"
    )
    download_successful = get_pdf(XXXLUTZ_VOUCHER_URL, temp_voucher_path)

    if not download_successful:
        logger.error(
            f"get_pdf failed to download voucher from {XXXLUTZ_VOUCHER_URL} to {temp_voucher_path}. Main download logic will not proceed."
        )
        # Still return true if a valid new_voucher_path exists from a previous successful run.
        return os.path.exists(new_voucher_path)

    try:
        if (
            not os.path.exists(temp_voucher_path)
            or os.path.getsize(temp_voucher_path) < MIN_VOUCHER_PDF_SIZE_BYTES
        ):
            logger.error(
                f"Downloaded voucher at {temp_voucher_path} is missing or too small (Size: {os.path.getsize(temp_voucher_path) if os.path.exists(temp_voucher_path) else 'N/A'} bytes). Minimum: {MIN_VOUCHER_PDF_SIZE_BYTES}"
            )
            # Clean up small/invalid temp file if it exists
            if os.path.exists(temp_voucher_path):
                try:
                    os.remove(temp_voucher_path)
                except OSError as e:
                    logger.error(
                        f"Error removing invalid temp voucher {temp_voucher_path}: {e}"
                    )
            return os.path.exists(
                new_voucher_path
            )  # Return status of existing new_voucher_path

        logger.info(
            f"Voucher downloaded to {temp_voucher_path} (Size: {os.path.getsize(temp_voucher_path)} bytes). Proceeding with version check."
        )

        if not os.path.exists(new_voucher_path):
            shutil.move(temp_voucher_path, new_voucher_path)
            logger.info(
                f"First XXXLutz voucher PDF downloaded and saved to {new_voucher_path}"
            )
            return True

        new_voucher_size = os.path.getsize(new_voucher_path)
        temp_voucher_size = os.path.getsize(temp_voucher_path)
        need_rotation = temp_voucher_size != new_voucher_size

        if not need_rotation:
            try:
                new_voucher_mtime = os.path.getmtime(new_voucher_path)
                current_time = time.time()
                if (current_time - new_voucher_mtime) > VOUCHER_MAX_AGE_SECONDS:
                    logger.info(
                        f"Voucher at {new_voucher_path} is older than {VOUCHER_MAX_AGE_SECONDS // (24 * 60 * 60)} days. Rotating."
                    )
                    need_rotation = True
            except FileNotFoundError:
                logger.warning(
                    f"New voucher file {new_voucher_path} not found when checking age. Assuming rotation needed if sizes differ or temp is valid."
                )
                # If new_voucher_path doesn't exist but temp_voucher_path is valid, we should treat it as a new download scenario.
                # This case is largely handled by the initial check for new_voucher_path existence.
            except Exception as e:
                logger.warning(
                    f"Error checking voucher file age for {new_voucher_path}: {e}. Proceeding with size-based rotation logic."
                )

        if need_rotation:
            if os.path.exists(old_voucher_path):
                try:
                    os.remove(old_voucher_path)
                except OSError as e:
                    logger.error(
                        f"Error removing old_voucher_path {old_voucher_path}: {e}"
                    )
            try:
                shutil.move(new_voucher_path, old_voucher_path)
                logger.info(f"Moved current {new_voucher_path} to {old_voucher_path}")
            except Exception as e:
                logger.error(
                    f"Error moving {new_voucher_path} to {old_voucher_path}: {e}"
                )
                # If this move fails, we might not want to overwrite new_voucher_path with temp_voucher_path
                # For now, we'll log and attempt to move temp to new anyway, which might fail or overwrite.

            shutil.move(temp_voucher_path, new_voucher_path)
            logger.info(
                f"Updated XXXLutz voucher: {temp_voucher_path} moved to {new_voucher_path}"
            )
        else:
            logger.info(
                f"XXXLutz voucher PDF at {new_voucher_path} is already up to date. Removing {temp_voucher_path}."
            )
            if os.path.exists(temp_voucher_path):
                try:
                    os.remove(temp_voucher_path)
                except OSError as e:
                    logger.error(
                        f"Error removing {temp_voucher_path} when voucher is up to date: {e}"
                    )
        return True

    except Exception as e:
        logger.error(
            f"Overall error in download_and_manage_xxxlutz_vouchers after get_pdf call: {e}"
        )
        logger.error(traceback.format_exc())
        # Clean up temp file if it exists and something went wrong
        if os.path.exists(temp_voucher_path):
            try:
                os.remove(temp_voucher_path)
            except OSError as e_clean:
                logger.error(
                    f"Error cleaning up {temp_voucher_path} in exception handler: {e_clean}"
                )
        return os.path.exists(
            new_voucher_path
        )  # Return true if a usable voucher still exists


def process_menu_image_and_update_meals(png_path):
    logger.info(f"Starting meal processing from PNG: {png_path}")
    if not os.path.exists(png_path):
        logger.error(f"PNG file not found at {png_path}. Cannot process menu.")
        return

    # 1. Encode image to base64
    try:
        with open(png_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode("utf-8")
    except Exception as e:
        logger.error(f"Error encoding image {png_path} to base64: {e}")
        return

    # 2. Call Mistral API (Pixtral - assuming mistral-large-latest is the one for now)
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        logger.error(
            "MISTRAL_API_KEY not found in environment. Cannot process menu image."
        )
        return

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    # Carefully craft the prompt for structured output
    # Using a regular triple-quoted string for the multiline prompt.
    # The example JSON structure is embedded directly.
    prompt_text = (
        "Analyze the attached menu image. Extract the main date visible on the menu (usually at the top, format it as DD.MM.YYYY). "
        "Then, specifically look for a section titled 'Hauptspeise' or 'Hauptspeisen'. Under this section, list the first two distinct meal descriptions you can find. "
        "Provide the output ONLY in the following JSON format, with no other text before or after the JSON block:\n"
        '{ "date": "DD.MM.YYYY", "meals": ["Meal 1 Description from Hauptspeise", "Meal 2 Description from Hauptspeise"] }\n'
        "If you cannot find a date, the 'Hauptspeise' section, or two distinct meals under it, provide null for the missing fields in the JSON. "
        "Ensure the meal descriptions are complete as seen on the menu under the 'Hauptspeise' section."
    )

    payload = {
        "model": "pixtral-12b-2409",  # Changed to specific Pixtral model
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_text},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{base64_image}"},
                    },
                ],
            }
        ],
        "temperature": 0.1,  # Lower temperature for more deterministic output
        "max_tokens": 500,
    }

    try:
        logger.info("Sending request to Mistral API for menu image processing...")
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=90,
        )
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        api_response = response.json()
        logger.debug(f"Mistral API raw response: {api_response}")

        content_str = (
            api_response.get("choices", [{}])[0].get("message", {}).get("content", "")
        )
        logger.info(f"Mistral API response content: {content_str}")

        # Attempt to parse the JSON from the content string
        # Clean the string: remove potential markdown backticks for JSON block
        if content_str.startswith("```json"):
            content_str = content_str[len("```json") :]
        if content_str.endswith("```"):
            content_str = content_str[: -len("```")]
        content_str = content_str.strip()

        parsed_content = json.loads(content_str)
        menu_date_str = parsed_content.get("date")
        extracted_meals = parsed_content.get("meals", [])

        if not menu_date_str or not extracted_meals or len(extracted_meals) < 1:
            logger.warning(
                f"Mistral API did not return the expected data structure or was missing date/meals. Date: {menu_date_str}, Meals: {extracted_meals}"
            )
            return

    except requests.exceptions.RequestException as e:
        logger.error(f"Mistral API request failed: {e}")
        if hasattr(e, "response") and e.response is not None:
            logger.error(f"Mistral API response content: {e.response.text}")
        return
    except json.JSONDecodeError as e:
        logger.error(
            f"Failed to parse JSON from Mistral response: {e}. Response was: {content_str}"
        )
        return
    except Exception as e:
        logger.error(f"Error processing Mistral API response: {e}")
        logger.error(traceback.format_exc())
        return

    # 3. Parse date and check if recent
    try:
        menu_date = datetime.strptime(menu_date_str, "%d.%m.%Y").date()
    except ValueError:
        logger.error(
            f"Invalid date format '{menu_date_str}' from Mistral. Cannot parse."
        )
        return

    today = date.today()
    update_meals_anyway = False

    # Check if there are any existing XXXLutzChangingMeal entries
    with app.app_context():  # Context needed for DB query
        existing_meal_count = XXXLutzChangingMeal.query.count()
        if existing_meal_count == 0:
            logger.info(
                "No existing XXXLutz changing meals found in the database. Meals will be updated even if the menu date is in the past."
            )
            update_meals_anyway = True

    # Check if the menu_date is today or in the future, OR if we should update anyway because DB is empty.
    if not update_meals_anyway and menu_date < today:
        logger.info(
            f"Menu date {menu_date_str} is in the past (today is {today.strftime('%d.%m.%Y')}) and database is not empty. XXXLutz meals will not be updated."
        )
        return

    if update_meals_anyway and menu_date < today:
        logger.info(
            f"Menu date {menu_date_str} is in the past, but updating because the database of XXXLutz changing meals is empty."
        )
    else:
        logger.info(
            f"Menu date {menu_date_str} ({menu_date.strftime('%A')}) is current or in the future. Proceeding to update XXXLutz changing meals."
        )

    # 4. Update XXXLutzChangingMeal in database
    with app.app_context():  # Ensure we have an app context for database operations
        try:
            # Clear existing changing meals
            num_deleted = XXXLutzChangingMeal.query.delete()
            logger.info(f"Deleted {num_deleted} existing XXXLutz changing meals.")

            # Add new meals (first two, or fewer if less than two extracted)
            for i, meal_desc in enumerate(extracted_meals[:2]):
                if meal_desc:  # Ensure description is not null or empty
                    new_meal = XXXLutzChangingMeal(
                        description=meal_desc,
                        marking="",  # Default
                        price_student=0.0,  # Default
                        price_employee=0.0,  # Default
                        price_guest=0.0,  # Default
                        nutritional_values="",  # Default
                    )
                    db.session.add(new_meal)
                    logger.info(f"Adding new XXXLutz changing meal: {meal_desc}")

            db.session.commit()
            logger.info("Successfully updated XXXLutz changing meals in the database.")

        except Exception as e:
            logger.error(f"Database error while updating XXXLutz changing meals: {e}")
            db.session.rollback()
            logger.error(traceback.format_exc())


# Create tables and load data
with app.app_context():
    # Initialize global data structures that will be populated by refresh functions
    mensa_data = {}  # Populated by refresh_mensa_xml_data
    available_mensen = []  # Populated by refresh_mensa_xml_data
    available_dates = []  # Populated by refresh_mensa_xml_data

    # Create database tables and perform initial data loads
    with app.app_context():
        db.create_all()
        logger.info("Database tables created (if not exist).")

        # Load XXXLutz FIXED meals. Changing meals are handled by menu_hg processing.
        # load_xxxlutz_meals() clears changing meals, so it's fine to call before menu_hg processing.
        logger.info("Loading XXXLutz fixed meals into database at startup...")
        if load_xxxlutz_meals():  # This function is from data_loader.py
            logger.info("Successfully loaded XXXLutz fixed meals.")
        else:
            logger.error("Failed to load XXXLutz fixed meals.")

    # Perform initial loads for all dynamic data sources
    # These functions now manage their own app_context for DB/app config access.
    perform_all_initial_loads()

    # Start the background refresh thread
    logger.info("Starting background data refresh thread...")
    refresh_thread = threading.Thread(target=background_scheduler, daemon=True)
    refresh_thread.start()
    logger.info("Background data refresh thread initiated.")


@app.route("/")
def index():
    # Use the data loaded at startup
    global mensa_data, available_mensen, available_dates

    # Data (`mensa_data`, `available_mensen`, `available_dates`) is loaded at startup
    # and refreshed periodically by the background scheduler.

    # Increment the page view counter (with error handling)
    try:
        page_view = PageView.query.first()
        if page_view is None:
            # Create new PageView with default count=0, then increment it
            page_view = PageView()
            db.session.add(page_view)
            db.session.commit()  # Commit to get the ID
            page_view.count = 1
        else:
            page_view.count += 1
        db.session.commit()
    except Exception as e:
        logger.error(f"Error updating page view counter: {e}")
        db.session.rollback()  # Roll back in case of error

    selected_date = request.args.get("date")
    selected_mensa = request.args.get("mensa")

    # Get today's date in the format used in the data
    today = datetime.now().strftime("%d.%m.%Y")
    today_dt = datetime.now()

    # Filter dates to only include -5 to +10 days from today
    filtered_dates = []
    for date_str in available_dates:
        try:
            date_obj = datetime.strptime(date_str, "%d.%m.%Y")
            days_diff = (date_obj - today_dt).days
            if -5 <= days_diff <= 10:
                filtered_dates.append(date_str)
        except ValueError as e:
            logger.warning(f"Skipping unparsable date_str: {date_str} - {e}")
            pass

    # Sort the filtered dates
    filtered_dates.sort(key=lambda x: datetime.strptime(x, "%d.%m.%Y"))
    # Removed DEBUG logs for date filtering

    # Default to today's date if available. If not, try to find the next available date.
    if not selected_date:  # If no date was passed as a query parameter
        if today in filtered_dates:
            selected_date = today
            # logger.debug(f"Defaulting to today's date: {selected_date}") # Removed DEBUG log
        else:
            # Removed DEBUG logs for next available day search
            selected_date_candidate = None
            if filtered_dates:
                for date_str_in_loop in filtered_dates:
                    try:
                        current_list_date_obj = datetime.strptime(
                            date_str_in_loop, "%d.%m.%Y"
                        ).date()
                        # Removed DEBUG logs for date comparison
                        if current_list_date_obj >= today_dt.date():
                            selected_date_candidate = date_str_in_loop
                            logger.info(
                                f"Found next available date (or today if it was parsed differently but matches): {selected_date_candidate}"
                            )
                            break  # Found the first suitable date
                        # else: # Removed DEBUG log for past date check
                            # logger.debug(
                            #     f"{date_str_in_loop} is in the past compared to today."
                            # )
                    except ValueError:
                        logger.warning(
                            f"Invalid date format '{date_str_in_loop}' in filtered_dates during next day search."
                        )
                        continue

                # If no future/current date was found after checking all, use the first available date as a last resort.
                if not selected_date_candidate and filtered_dates:
                    selected_date_candidate = filtered_dates[0]
                    logger.info(
                        f"No future/current date found in filtered_dates. Defaulting to the first date in the list: {selected_date_candidate}"
                    )

                selected_date = selected_date_candidate
            else:
                logger.warning(
                    "No dates available in filtered_dates to select any default."
                )
                # selected_date remains None or its previous value if any

    # Set default mensa to "Mensa Garbsen" if not selected
    if not selected_mensa:
        selected_mensa = "Mensa Garbsen"

    # Filter the available mensen to only include the required ones
    allowed_mensen = ["Mensa Garbsen", "Hauptmensa", "Contine"]
    filtered_mensen = [mensa for mensa in available_mensen if mensa in allowed_mensen]

    # Mapping for mensa emojis
    mensa_emojis = {
        "Mensa Garbsen": "🤖",
        "Contine": "🤑",
        "Hauptmensa": "👷",
        "XXXLutz Hesse Markrestaurant": "🪑",
    }

    # If mensa is specified, show only that one, otherwise show allowed mensen
    filtered_data = {}

    # Include the selected mensa first
    if selected_mensa in mensa_data and selected_date in mensa_data[selected_mensa]:
        meals = mensa_data[selected_mensa][selected_date]

        # Look up IDs from the database for each meal with error handling
        for meal in meals:
            try:
                # Find the meal in the database by description
                db_meal = Meal.query.filter_by(description=meal["description"]).first()
                if db_meal:
                    meal["id"] = db_meal.id
                else:
                    # If not found, use a placeholder ID
                    meal["id"] = 0
            except Exception as e:
                logger.error(f"Error looking up meal in database: {e}")
                meal["id"] = 0  # Use placeholder ID in case of error

        sorted_meals = sorted(
            meals,
            key=lambda meal: calculate_caner(
                extract_kcal(meal["nutritional_values"]), meal["price_student"]
            ),
            reverse=True,
        )
        filtered_data[selected_mensa] = sorted_meals

        # Add XXXLutz Hesse Markrestaurant menu if Mensa Garbsen is selected
        if selected_mensa == "Mensa Garbsen":
            # Get XXXLutz meals from database
            xxxlutz_meals = []

            # Get changing meals
            changing_meals = XXXLutzChangingMeal.query.all()
            for meal in changing_meals:
                xxxlutz_meals.append(
                    {
                        "id": str(meal.id),
                        "description": meal.description,
                        "marking": meal.marking,
                        "price_student": f"{meal.price_student:.2f}".replace(".", ","),
                        "price_employee": f"{meal.price_employee:.2f}".replace(
                            ".", ","
                        ),
                        "price_guest": f"{meal.price_guest:.2f}".replace(".", ","),
                        "nutritional_values": meal.nutritional_values,
                        "category": "Wechselnde Gerichte Woche",
                    }
                )

            # Get fixed meals
            fixed_meals = XXXLutzFixedMeal.query.all()
            for meal in fixed_meals:
                xxxlutz_meals.append(
                    {
                        "id": str(meal.id),
                        "description": meal.description,
                        "marking": meal.marking,
                        "price_student": f"{meal.price_student:.2f}".replace(".", ","),
                        "price_employee": f"{meal.price_employee:.2f}".replace(
                            ".", ","
                        ),
                        "price_guest": f"{meal.price_guest:.2f}".replace(".", ","),
                        "nutritional_values": meal.nutritional_values,
                        "category": "Ständiges Angebot",
                    }
                )

            # Assign IDs to XXXLutz meals
            for meal in xxxlutz_meals:
                # First check if it's a changing meal
                if meal["category"] == "Wechselnde Gerichte Woche":
                    db_meal = XXXLutzChangingMeal.query.filter_by(
                        description=meal["description"]
                    ).first()
                else:
                    # Then check if it's a fixed meal
                    db_meal = XXXLutzFixedMeal.query.filter_by(
                        description=meal["description"]
                    ).first()

                if db_meal:
                    meal["id"] = str(db_meal.id)
                else:
                    # Create a synthetic ID for XXXLutz meals
                    # We'll use a negative number to distinguish them from regular meals
                    # and avoid conflicts with the database
                    meal["id"] = "-1"

            # Sort the meals with the weekly meals first, followed by the static menu
            sorted_xxxlutz_meals = sorted(
                xxxlutz_meals,
                key=lambda meal: 0
                if meal["category"] == "Wechselnde Gerichte Woche"
                else 1,
            )

            # Add to filtered data
            filtered_data["XXXLutz Hesse Markrestaurant"] = sorted_xxxlutz_meals

    # If no mensa is selected, include others from allowed list
    if not selected_mensa or selected_mensa == "":
        for mensa in allowed_mensen:
            if (
                mensa in mensa_data
                and selected_date in mensa_data[mensa]
                and mensa not in filtered_data
            ):
                meals = mensa_data[mensa][selected_date]

                # Look up IDs from the database for each meal
                for meal in meals:
                    # Find the meal in the database by description
                    db_meal = Meal.query.filter_by(
                        description=meal["description"]
                    ).first()
                    if db_meal:
                        meal["id"] = str(db_meal.id)
                    else:
                        # If not found, use a placeholder ID
                        meal["id"] = "0"

                sorted_meals = sorted(
                    meals,
                    key=lambda meal: calculate_caner(
                        extract_kcal(meal["nutritional_values"]), meal["price_student"]
                    ),
                    reverse=True,
                )
                filtered_data[mensa] = sorted_meals

    # Get the current page view count to display in the template
    current_page_views = 0
    try:
        page_view_obj = PageView.query.first()
        current_page_views = page_view_obj.count if page_view_obj else 0
    except Exception as e:
        logger.error(f"Error retrieving page view count: {e}")

    return render_template(
        "index.html",
        data=filtered_data,
        available_mensen=filtered_mensen,
        available_dates=filtered_dates,
        selected_date=selected_date,
        selected_mensa=selected_mensa,
        mensa_emojis=mensa_emojis,
        page_views=current_page_views,
    )


@app.template_filter("format_date")
def format_date(date_str):
    try:
        date_obj = datetime.strptime(date_str, "%d.%m.%Y")

        # Map weekday number to German weekday name
        weekdays = [
            "Montag",
            "Dienstag",
            "Mittwoch",
            "Donnerstag",
            "Freitag",
            "Samstag",
            "Sonntag",
        ]
        weekday = weekdays[date_obj.weekday()]

        # Format as "DD.MM.YYYY, Weekday"
        return f"{date_obj.strftime('%d.%m.%Y')}, {weekday}"
    except ValueError as e:
        logger.warning(
            f"Returning original date_str due to ValueError: {date_str} - {e}"
        )
        return date_str
    except Exception as e:  # General exception handler
        logger.error(
            f"An unexpected error occurred in format_date with {date_str}: {e}"
        )
        return date_str


@app.template_filter("extract_kcal")
def extract_kcal(naehrwert_str):
    try:
        # Example: Brennwert=3062 kJ (731 kcal), Fett=8,4g...
        if "kcal" in naehrwert_str:
            start = naehrwert_str.index("(") + 1
            end = naehrwert_str.index("kcal")
            return int(naehrwert_str[start:end].strip())
        return 0
    except Exception as e:
        logger.error(
            f"An unexpected error occurred in extract_kcal with {naehrwert_str}: {e}"
        )
        return 0


@app.template_filter("calculate_caner")
def calculate_caner(kcal, price_student):
    # Input validation for price_student
    if price_student is None or not isinstance(price_student, str) or price_student.strip() == "":
        logger.warning(
            f"Invalid price_student input in calculate_caner: Received '{price_student}' (type: {type(price_student)}). Treating as 0."
        )
        return 0

    try:
        # Attempt to convert price from string to float (replace comma with dot)
        price_str_cleaned = price_student.replace(",", ".").strip()
        price = float(price_str_cleaned)

        # Check for non-positive price after conversion
        if price <= 0:
            logger.warning(
                f"Non-positive price detected in calculate_caner: kcal={kcal}, price_student='{price_student}' resulted in price={price}. Treating as 0."
            )
            return 0

        # Ensure kcal is a number (it should be from extract_kcal)
        if not isinstance(kcal, (int, float)):
             logger.warning(
                f"Invalid kcal input in calculate_caner: Received '{kcal}' (type: {type(kcal)}). Cannot calculate Caner score."
            )
             return 0

        # Calculate and return Caner score
        return round(kcal / price, 2)

    except ValueError:
        # Log specific error if float conversion fails
        logger.warning(
            f"Could not convert price_student='{price_student}' to float in calculate_caner. Original kcal={kcal}. Treating as 0."
        )
        return 0
    except Exception as e:
        # Catch any other unexpected errors
        logger.error(
            f"An unexpected error occurred in calculate_caner with kcal={kcal}, price_student='{price_student}': {e}"
        )
        logger.error(traceback.format_exc()) # Log stack trace for unexpected errors
        return 0


@app.template_filter("generate_caner_symbols")
def generate_caner_symbols(caner_score):
    if caner_score <= 0:
        return ""

    # Format the caner value with 2 decimal places and comma as decimal separator
    caner_value_formatted = f"{caner_score:.2f}".replace(".", ",")

    # Calculate full icons (100s) and partial icon percentage
    full_icons = int(
        caner_score // 100
    )  # Remove the min(5, ...) to allow more than 5 icons
    remainder = caner_score % 100

    has_partial = remainder > 0
    partial_percentage = int(remainder)  # Percentage of the next 100

    # Generate HTML for the icons
    icons_html_parts = []

    # Add full icons
    for _ in range(full_icons):
        icons_html_parts.append(
            '<img src="/static/img/caner.png" class="caner-icon light-caner">'
            '<img src="/static/img/darkcaner.png" class="caner-icon dark-caner">'
        )

    # Add partial icon if needed
    if has_partial:
        # Calculate width based on percentage (18px is the icon width)
        width_px = (18 * partial_percentage) / 100

        # Create partial icon with cropped width
        icons_html_parts.append(
            f'<span class="caner-icon-partial" style="--crop-percentage: {width_px}px">'
            '<img src="/static/img/caner.png" class="light-caner">'
            '<img src="/static/img/darkcaner.png" class="dark-caner">'
            "</span>"
        )

    icons_html = "".join(icons_html_parts)
    return f'<span class="caner-symbol">{icons_html}</span><span class="caner-value">{caner_value_formatted}</span>'


@app.template_filter("get_dietary_info")
def get_dietary_info(marking):
    """Extract dietary information from marking codes and show as emojis with tooltips"""
    if not marking:
        return ""

    markings = marking.lower().replace(" ", "").split(",")

    # Define mapping of codes to emojis and descriptions
    marking_info = {
        "v": {"emoji": "🥕", "title": "Vegetarisch"},
        "x": {"emoji": "🥦", "title": "Vegan"},
        "g": {"emoji": "🐔", "title": "Geflügel"},
        "s": {"emoji": "🐷", "title": "Schwein"},
        "f": {"emoji": "🐟", "title": "Fisch"},
        "r": {"emoji": "🐮", "title": "Rind"},
        "a": {"emoji": "🍺", "title": "Alkohol"},
        "26": {"emoji": "🥛", "title": "Milch"},
        "22": {"emoji": "🥚", "title": "Ei"},
        "20a": {"emoji": "🌾", "title": "Weizen"},
    }

    emoji_spans = []
    for code in markings:
        if code in marking_info:
            emoji = marking_info[code]["emoji"]
            title = marking_info[code]["title"]
            emoji_spans.append(
                f'<span class="food-marking" title="{title}">{emoji}</span>'
            )

    return " ".join(emoji_spans)


# Get or create a client ID from cookie
def get_client_id():
    client_id = request.cookies.get("client_id")
    if not client_id:
        client_id = str(uuid.uuid4())
    return client_id


# Get meal vote counts for a specific meal
def get_vote_counts(meal_id):
    # Convert to integer if it's a string
    meal_id_int = int(meal_id) if isinstance(meal_id, str) else meal_id
    upvotes = MealVote.query.filter_by(meal_id=meal_id_int, vote_type="up").count()
    downvotes = MealVote.query.filter_by(meal_id=meal_id_int, vote_type="down").count()
    return {"up": upvotes, "down": downvotes}


# Check if a client has already voted for a meal today
def has_voted_today(meal_id, client_id):
    # Convert to integer if it's a string
    meal_id_int = int(meal_id) if isinstance(meal_id, str) else meal_id
    today = date.today()
    vote = MealVote.query.filter_by(
        meal_id=meal_id_int, client_id=client_id, date=today
    ).first()
    return vote is not None


# API route to handle meal votes
@app.route("/api/vote", methods=["POST"])
def vote():
    data = request.json
    if not data:
        return jsonify({"error": "Invalid JSON data"}), 400

    # Get data from request
    meal_id = data.get("meal_id")
    vote_type = data.get("vote_type")  # 'up' or 'down'

    # Validate input
    if not meal_id or vote_type not in ["up", "down"]:
        return jsonify({"error": "Invalid input"}), 400

    # Convert to integer if it's a string
    meal_id_int = int(meal_id) if isinstance(meal_id, str) else meal_id

    # Check if meal exists
    meal = Meal.query.get(meal_id_int)
    if not meal:
        return jsonify({"error": "Meal not found"}), 404

    # Get or set client ID from cookie
    client_id = get_client_id()
    today = date.today()

    # Check if client already voted for this meal today
    existing_vote = MealVote.query.filter_by(
        meal_id=meal_id_int, client_id=client_id, date=today
    ).first()

    if existing_vote:
        # If vote type is different, update it
        if existing_vote.vote_type != vote_type:
            existing_vote.vote_type = vote_type
            db.session.commit()
            message = "Vote updated"
        else:
            message = "Already voted"
    else:
        # Create new vote
        new_vote = MealVote()
        new_vote.meal_id = meal_id_int
        new_vote.client_id = client_id
        new_vote.date = today
        new_vote.vote_type = vote_type
        db.session.add(new_vote)
        db.session.commit()
        message = "Vote recorded"

    # Get updated vote counts
    vote_counts = get_vote_counts(meal_id)

    # Create response with cookie
    response = make_response(jsonify({"message": message, "votes": vote_counts}))

    # Set client ID cookie (expires in 1 year)
    response.set_cookie("client_id", client_id, max_age=60 * 60 * 24 * 365)

    return response


# API route to get vote counts for a meal
@app.route("/api/votes/<int:meal_id>", methods=["GET"])
def get_votes(meal_id):
    # Check if meal exists
    meal = Meal.query.get(meal_id)
    if not meal:
        return jsonify({"error": "Meal not found"}), 404

    # Get client ID from cookie if exists
    client_id = get_client_id()

    # Get vote counts
    vote_counts = get_vote_counts(meal_id)

    # Check if client has already voted
    has_voted = has_voted_today(meal_id, client_id)

    # Create response with cookie
    response = make_response(jsonify({"votes": vote_counts, "has_voted": has_voted}))

    # Set client ID cookie if new
    if not request.cookies.get("client_id"):
        response.set_cookie("client_id", client_id, max_age=60 * 60 * 24 * 365)

    return response


@app.route("/download-voucher/<voucher_type>")
def download_voucher(voucher_type):
    """
    Download XXXLutz vouchers.
    voucher_type can be 'new' for 'Neue Gutscheine' or 'old' for 'Alte Gutscheine'
    """
    # Ensure we have a valid static folder path
    static_folder = app.static_folder if app.static_folder else "static"
    vouchers_dir = os.path.join(static_folder, "vouchers")

    if voucher_type == "new":
        filename = "neue_gutscheine.pdf"
    elif voucher_type == "old":
        filename = "alte_gutscheine.pdf"
    else:
        return "Invalid voucher type", 400

    # Check if the file exists (should be populated by background task)
    file_path = os.path.join(vouchers_dir, filename)
    if not os.path.exists(file_path):
        logger.warning(
            f"Voucher file {filename} not found in {vouchers_dir}. Background task might not have run or failed."
        )
        return (
            "Voucher not available. It is updated periodically. Please check back later.",
            404,
        )

    logger.info(f"Serving voucher: {filename} from {vouchers_dir}")
    # Set appropriate headers for PDF
    return send_from_directory(
        vouchers_dir,
        filename,
        as_attachment=True,
        mimetype="application/pdf",
        download_name=f"xxxlutz_{voucher_type}_gutscheine.pdf",
    )


@app.route("/download-menu-hg")
def download_menu_hg_pdf():
    """
    Serves the menu_hg.pdf file previously downloaded and stored
    by the background refresh task.
    """
    static_folder = app.static_folder if app.static_folder else "static"
    menu_dir = os.path.join(static_folder, "menu")
    os.makedirs(menu_dir, exist_ok=True)  # Ensure menu directory exists
    filename = "menu_hg.pdf"
    pdf_path = os.path.join(menu_dir, filename)  # Updated path

    # This route now serves the PDF that is periodically downloaded and processed by the background task.
    static_folder = app.static_folder if app.static_folder else "static"
    menu_dir = os.path.join(static_folder, "menu")
    os.makedirs(menu_dir, exist_ok=True)
    filename = "menu_hg.pdf"
    pdf_path = os.path.join(menu_dir, filename)

    if (
        not os.path.exists(pdf_path)
        or os.path.getsize(pdf_path) < MIN_MENU_HG_PDF_SIZE_BYTES
    ):
        logger.warning(
            f"Menu HG PDF ({pdf_path}) not found or too small to serve. Background task might not have run or failed."
        )
        return (
            "Menu HG PDF is not currently available. It is updated periodically. Please try again later.",
            404,
        )

    logger.info(f"Serving existing Menu HG PDF: {pdf_path}")
    return send_from_directory(
        menu_dir,
        filename,
        as_attachment=True,
        mimetype="application/pdf",
        download_name="menu_hg.pdf",
    )


@app.route("/menu-hg-image")
def get_menu_hg_image():
    """
    Serves the menu_hg.png image previously converted and stored
    by the background refresh task.
    """
    # Ensure we have a valid static folder path
    static_folder = app.static_folder if app.static_folder else "static"
    menu_dir = os.path.join(static_folder, "menu")  # Changed from vouchers_dir
    os.makedirs(menu_dir, exist_ok=True)  # Ensure menu directory exists

    # This route now serves the PNG that is periodically converted by the background task.
    static_folder = app.static_folder if app.static_folder else "static"
    menu_dir = os.path.join(static_folder, "menu")
    os.makedirs(
        menu_dir, exist_ok=True
    )  # Ensure menu directory exists, though background task should create it

    png_filename = "menu_hg.png"
    png_path = os.path.join(menu_dir, png_filename)

    if (
        not os.path.exists(png_path)
        or os.path.getsize(png_path) < MIN_MENU_HG_PNG_SIZE_BYTES
    ):
        logger.warning(
            f"Menu HG PNG ({png_path}) not found or too small to serve. Background task might not have run or conversion failed."
        )
        return (
            "Menu HG image is not currently available. It is updated periodically. Please try again later.",
            404,
        )

    logger.info(f"Serving existing Menu HG PNG: {png_path}")
    return send_from_directory(menu_dir, png_filename, mimetype="image/png")


@app.route("/api/get_trump_recommendation", methods=["POST"])
def get_trump_recommendation():
    """Get a meal recommendation from the Mistral API as Donald Trump (English)"""
    try:
        data = request.json
        if data is None:
            return jsonify({"error": "Invalid JSON provided"}), 400
        available_meals = data.get("meals", [])

        if not available_meals:
            return jsonify({"error": "No meals provided"}), 400

        # Format meals for the prompt
        meal_list_for_prompt = "\n".join([f"- {meal}" for meal in available_meals])

        # Construct the prompt in English with Trump persona
        prompt = (
            "You are Donald Trump. Review the following menu items available at Contine. "
            "Provide your recommendation in English in the style of Donald Trump, "
            "briefly explaining why. Use confident and extravagant language. "
            "Do NOT repeat the menu list. Only return your personal recommendation!'\n\n"
            "Menu Items:\n" + meal_list_for_prompt
        )

        api_key = os.environ.get("MISTRAL_API_KEY")
        if not api_key:
            logger.error(
                "MISTRAL_API_KEY not found in environment for Trump recommendation."
            )
            return jsonify({"error": "Mistral API key not configured"}), 500

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers=headers,
            json={
                "model": "mistral-small-latest",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 200,
            },
        )

        if response.status_code == 200:
            result = response.json()
            recommendation = (
                result.get("choices", [{}])[0].get("message", {}).get("content", "")
            )
            # Clean markdown if present
            if recommendation.startswith("```"):
                recommendation = recommendation.strip("`")
            # Trim any leading phrases
            recommendation = recommendation.strip()
            return jsonify({"recommendation": recommendation})
        else:
            logger.error(
                f"Trump Mistral API error: {response.status_code} - {response.text}"
            )
            return jsonify(
                {"error": "Error from Mistral API", "details": response.text}
            ), 500

    except Exception as e:
        logger.error(f"Error in get_trump_recommendation: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@app.route("/api/get_bob_recommendation", methods=["POST"])
def get_bob_recommendation():
    """Get a meal recommendation from the Mistral API as Bob der Baumeister (German)"""
    try:
        data = request.json
        if data is None:
            return jsonify({"error": "Invalid JSON provided"}), 400
        available_meals = data.get("meals", [])

        if not available_meals:
            return jsonify({"error": "Keine Gerichte angegeben"}), 400

        # Format meals for the prompt
        meal_list_for_prompt = "\n".join([f"- {meal}" for meal in available_meals])

        # Construct the German prompt for Bob der Baumeister
        prompt = (
            "Du bist Bob der Baumeister, der freundlichste Baumeister der Welt. "
            "Erinnere uns daran, einen Helm zu tragen, denn die Decke der Hauptmensa "
            "könnte jederzeit einstürzen.\n\n"
            "Verfügbare Gerichte:\n" + meal_list_for_prompt + "\n\n"
            "Empfiehl in einem kurzen Satz auf Deutsch genau ein Gericht, im Stil von Bob: "
            "'Ich empfehle [GERICHT], weil [GRUND], vergiss deinen Helm nicht.'"
        )

        api_key = os.environ.get("MISTRAL_API_KEY")
        if not api_key:
            logger.error("MISTRAL_API_KEY nicht in der Umgebung für Bob gespeichert.")
            return jsonify({"error": "Mistral API-Schlüssel nicht konfiguriert"}), 500

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers=headers,
            json={
                "model": "mistral-small-latest",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 150,
            },
        )

        if response.status_code == 200:
            result = response.json()
            recommendation = (
                result.get("choices", [{}])[0].get("message", {}).get("content", "")
            )
            # Remove markdown if present
            if recommendation.startswith("```"):
                recommendation = recommendation.strip("`")
            recommendation = recommendation.strip()
            return jsonify({"recommendation": recommendation})
        else:
            logger.error(
                f"Bob Mistral API-Fehler: {response.status_code} - {response.text}"
            )
            return jsonify(
                {"error": "Fehler von Mistral API", "details": response.text}
            ), 500

    except Exception as e:
        logger.error(f"Fehler in get_bob_recommendation: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@app.route("/api/get_marvin_recommendation", methods=["POST"])
def get_marvin_recommendation():
    """Get a meal recommendation from the Mistral API, as Marvin (German)"""
    try:
        data = request.json
        if data is None:
            return jsonify({"error": "Invalid JSON provided"}), 400
        available_meals = data.get("meals", [])

        if not available_meals:
            return jsonify({"error": "No meals provided"}), 400

        meal_list_for_prompt = "\n".join([f"- {meal}" for meal in available_meals])

        # Prepare the German prompt for Marvin
        prompt_parts = [
            "Du bist Marvin, der depressive Roboter aus 'Per Anhalter durch die Galaxis'.",
            "Betrachte die folgende Liste von Gerichten, die heute zur Verfügung stehen. Es ist alles so sinnlos, aber gib trotzdem eine Empfehlung ab.",
            "Erkläre kurz und mit deiner typisch niedergeschlagenen, sarkastischen Art, warum du dieses Gericht wählen würdest (oder auch nicht).",
            "Versuche, dich auf ein Gericht zu konzentrieren.\n\n",
            "Verfügbare Gerichte:\n",
            meal_list_for_prompt,
            "\n\nDeine deprimierende Empfehlung (bitte gib nur den Empfehlungstext zurück, ohne einleitende Sätze wie 'Hier ist deine Empfehlung'):",
        ]
        prompt = "\n".join(prompt_parts)

        api_key = os.environ.get("MISTRAL_API_KEY")
        if not api_key:
            logger.error(
                "MISTRAL_API_KEY not found in environment for Marvin recommendation."
            )
            return jsonify({"error": "Mistral API key not configured"}), 500

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers=headers,
            json={
                "model": "mistral-small-latest",  # Or any other suitable model
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,  # A bit of creativity for Marvin
                "max_tokens": 200,  # Adjust as needed
            },
        )

        if response.status_code == 200:
            result = response.json()
            recommendation = (
                result.get("choices", [{}])[0].get("message", {}).get("content", "")
            )
            # Clean up potential markdown or extra phrases if the API adds them
            if recommendation.startswith("```json"):
                recommendation = recommendation[len("```json") :].rstrip("```").strip()
            elif recommendation.startswith("```"):
                recommendation = recommendation[len("```") :].rstrip("```").strip()

            # Remove common leading phrases if Marvin still includes them despite the prompt
            common_phrases_to_remove = [
                "Hier ist deine deprimierende Empfehlung:",
                "Meine deprimierende Empfehlung lautet:",
                "Deprimierende Empfehlung:",
            ]
            for phrase in common_phrases_to_remove:
                if recommendation.lower().startswith(phrase.lower()):
                    recommendation = recommendation[len(phrase) :].strip()

            return jsonify({"recommendation": recommendation.strip()})
        else:
            logger.error(
                f"Marvin Mistral API error: {response.status_code} - {response.text}"
            )
            return jsonify(
                {"error": "Error from Mistral API", "details": response.text}
            ), 500

    except Exception as e:
        logger.error(f"Error in get_marvin_recommendation: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500
