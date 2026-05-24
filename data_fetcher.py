import logging
import os
import sys
import time
import traceback

from dotenv import load_dotenv
from flask import Flask

from data_loader import load_xml_data_to_db
from fetch_meal_translations import fetch_meal_translations
from meal_translation import has_configured_translation_api_key
from models import db
from schema import ensure_application_schema


# --- Environment Variable Loading ---
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    print(f"Loaded environment variables from {dotenv_path}")
else:
    print(
        f"Warning: .env file not found at {dotenv_path}. Assuming environment variables are set externally."
    )

# --- Logging Configuration ---
logger = logging.getLogger("data_fetcher")
logger.setLevel(logging.DEBUG)

log_dir = os.environ.get("LOG_DIR", os.path.join(os.path.dirname(__file__), "logs"))
try:
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, "data_fetcher.log")
    file_handler = logging.FileHandler(log_file_path, mode="a")
except OSError:
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

logger.info(f"Logging initialized for data_fetcher. Log file at: {log_file_path}")


# --- Constants ---
XML_SOURCE_URL = (
    "https://www.studentenwerk-hannover.de/fileadmin/user_upload/Speiseplan/SP-UTF8.xml"
)


def env_flag(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


MEAL_TRANSLATION_ENABLED = env_flag("MEAL_TRANSLATION_ENABLED", True)
MEAL_TRANSLATION_BATCH_SIZE = int(os.environ.get("MEAL_TRANSLATION_BATCH_SIZE", "20"))
MEAL_TRANSLATION_WORKERS = int(os.environ.get("MEAL_TRANSLATION_WORKERS", "2"))


# --- Minimal Flask App for Context ---
app = Flask(__name__)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

database_url = os.environ.get("DATABASE_URL")

if not database_url:
    logger.error(
        "Database configuration missing. Please ensure DATABASE_URL is set."
    )
    sys.exit(1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url

try:
    db.init_app(app)
    logger.info("Database connection initialized for Flask-SQLAlchemy context.")
except Exception as e:
    logger.error(f"Failed to initialize db with Flask app: {e}")
    logger.error(traceback.format_exc())
    sys.exit(1)


if __name__ == "__main__":
    logger.info("=============================================")
    logger.info("Running Data Fetcher Script Manually")
    logger.info("=============================================")

    start_time = time.time()
    xml_success = False

    with app.app_context():
        db.create_all()
        ensure_application_schema(db)
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
            xml_success = False

        translation_success = False
        if xml_success and MEAL_TRANSLATION_ENABLED:
            if has_configured_translation_api_key():
                logger.info("--- Starting Missing English Meal Translation Fetch ---")
                translation_result = fetch_meal_translations(
                    overwrite_all=False,
                    batch_size=MEAL_TRANSLATION_BATCH_SIZE,
                    workers=MEAL_TRANSLATION_WORKERS,
                )
                translation_success = translation_result == 0
                if translation_success:
                    logger.info(
                        "--- Missing English Meal Translation Fetch Completed Successfully ---"
                    )
                else:
                    logger.warning(
                        "--- Missing English Meal Translation Fetch Finished With Exit Code %s ---",
                        translation_result,
                    )
            else:
                logger.warning(
                    "Skipping meal translation fetch because OPENROUTER_API_KEY is not configured."
                )
        elif not MEAL_TRANSLATION_ENABLED:
            logger.info("Meal translation fetch disabled by MEAL_TRANSLATION_ENABLED.")
            translation_success = True

    duration = time.time() - start_time

    logger.info("=============================================")
    logger.info(f"Data Fetcher Script Finished in {duration:.2f} seconds")
    logger.info(f"Mensa XML Refresh Success: {xml_success}")
    logger.info(f"Meal Translation Fetch Success: {translation_success}")
    logger.info("=============================================")

    sys.exit(0 if xml_success else 1)
