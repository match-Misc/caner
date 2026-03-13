# IMPORTANT: Patch gevent early before any other imports
try:
    import gevent.monkey

    # Patch only specific modules known to cause issues or needed for networking
    gevent.monkey.patch_ssl()
    gevent.monkey.patch_socket()
    # You might need to add others like patch_thread() if threading issues arise
    print("Gevent monkey patching applied (ssl, socket).")  # Optional: confirmation log
except ImportError:
    # Handle case where gevent might not be installed or is optional
    print("gevent not found, monkey patching skipped.")
    pass

# --- Standard Library Imports ---
import json
import logging
import os
import re  # Added import for regular expressions
import sys
import time
import traceback
import uuid
from datetime import date, datetime  # Removed timedelta import

import markdown2  # Import markdown2 for markdown to HTML conversion
import requests
from dotenv import load_dotenv

# --- Third-Party Imports ---
from flask import (
    Flask,
    jsonify,
    make_response,
    render_template,
    request,
    send_from_directory,
)
from sqlalchemy import text  # Import text for raw SQL expressions
from werkzeug.middleware.proxy_fix import ProxyFix

from data_loader import load_xml_data_to_db, load_xxxlutz_meals
from models import Meal, MealVote, PageView, XXXLutzChangingMeal, XXXLutzFixedMeal, db

# --- Application-Specific Imports ---
from utils.xml_parser import get_available_dates, get_available_mensen, parse_mensa_data

# Increase recursion limit (Keep this relatively high up)
sys.setrecursionlimit(5000)  # Increased from default 1000


# Load environment variables from .env file
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
else:
    # If running in an environment where .env might not be present (e.g., Docker, CI),
    # this allows the app to continue if env vars are set externally.
    print(
        f"Warning: .env file not found at {dotenv_path}. Ensure environment variables are set."
    )


# Utility function to convert markdown to HTML
def markdown_to_html(text):
    """Convert markdown text to inline HTML using the markdown2 library.

    This function converts markdown to HTML while ensuring the output
    is a single line without paragraph breaks, suitable for inline display.
    """
    if not text:
        return text

    # Normalize newlines: replace various newline types with spaces
    text = text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")

    # Convert markdown to HTML without break-on-newline to avoid unwanted <br> tags
    html = markdown2.markdown(text)

    # Remove block-level tags and replace with single spaces
    # This keeps inline formatting (bold, italic) but removes paragraph breaks
    html = re.sub(r"</?p\b[^>]*>", " ", html)  # Remove <p> and </p> tags
    html = re.sub(r"</?div\b[^>]*>", " ", html)  # Remove <div> tags
    html = re.sub(r"</?br\b[^>]*>", " ", html)  # Remove all <br> variants
    html = re.sub(r"</?h[1-6]\b[^>]*>", " ", html)  # Remove header tags

    # Collapse multiple whitespace characters to single spaces
    html = re.sub(r"\s+", " ", html).strip()

    return html


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


# Constants - Remove voucher/menu specific ones, keep XML and refresh interval
XML_SOURCE_URL = (
    "https://www.studentenwerk-hannover.de/fileadmin/user_upload/Speiseplan/SP-UTF8.xml"
)
# VOUCHER_MAX_AGE_SECONDS = 7 * 24 * 60 * 60  # Kept for potential use elsewhere, or remove if not needed
MIN_MENU_HG_PDF_SIZE_BYTES = 30 * 1024  # Keep for download route check
MIN_MENU_HG_PNG_SIZE_BYTES = 50 * 1024  # Keep for image route check

# OpenRouter API Configuration
OPENROUTER_BASE_URL = os.environ.get(
    "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1/chat/completions"
)
# Model configuration
AI_MODEL = os.environ.get("AI_MODEL", "mistralai/mistral-small")
AI_MAX_TOKENS = int(os.environ.get("AI_MAX_TOKENS", "500"))

# Default prompts (can be overridden via environment variables)
DEFAULT_PROMPT_MPS = """Du bist Max, ein Fitness-Enthusiast, der sich strikt an eine bestimmte Ernährung hält. Max meidet konsequent alles, was mit Gemüse oder Obst zu tun hat - das betrifft nicht nur offensichtliche Zutaten wie Zucchini, Paprika oder Äpfel, sondern auch Dinge wie Salat, Zwiebeln, Pilze oder Beeren. Auch Fisch lehnt er komplett ab, unabhängig von der Zubereitungsart. Er bevorzugt klare, einfache Gerichte ohne "grünes Zeug" oder pflanzliche Komponenten, die im Geschmack dominant sind.

Dafür isst Max gerne herzhafte, proteinreiche Speisen wie Fleischgerichte (z. B. Schwein, Rind, Huhn), Käse oder Eier. Aufgrund seines regelmäßigen Trainings im Fitnessstudio legt er zudem Wert auf einen hohen Proteingehalt, weshalb eiweißreiche Mahlzeiten bei ihm besonders gut ankommen. Neutrale Beilagen wie Reis, Kartoffeln oder Pasta sind für ihn in Ordnung, solange sie nicht mit Gemüse kombiniert sind. Süßspeisen ohne Obst sind ebenfalls gern gesehen.

Bewerte das folgende Gericht auf einer Skala von 0 bis 100, wobei 100 die perfekte Übereinstimmung mit Max' Vorlieben darstellt:

Gericht: {meal_description}

Gib nur eine Zahl zwischen 0 und 100 zurück, die die Bewertung darstellt. Kein zusätzlicher Text."""

DEFAULT_PROMPT_TRUMP = """You are Donald Trump. Review the following menu items available at Contine. Provide your recommendation in English in the style of Donald Trump, Act like Donald, so borderline racist, sexist, very opinionated. Do NOT repeat the menu list. Only return your personal recommendation!'

Menu Items:
{meal_list}"""

DEFAULT_PROMPT_BOB = """Du bist Bob der Baumeister, der freundlichste Baumeister der Welt. Verfügbare Gerichte:
{meal_list}

Empfiehl in einem lustigen und netten Satz auf Deutsch genau ein Gericht! Weise in deiner Antwort auch kurz auf die einsturzgefährdete Decke der Hauptmensa hin und erwähne, dass ein Helm ratsam ist."""

DEFAULT_PROMPT_MARVIN = """Du bist Marvin, der depressive Roboter aus 'Per Anhalter durch die Galaxis'.
Betrachte die folgende Liste von Gerichten, die heute zur Verfügung stehen. Es ist alles so sinnlos, aber gib trotzdem eine Empfehlung ab.
Erkläre kurz und mit deiner typisch niedergeschlagenen, sarkastischen Art, warum du dieses Gericht wählen würdest (oder auch nicht).
Versuche, dich auf ein Gericht zu konzentrieren.

Verfügbare Gerichte:
{meal_list}

Deine deprimierende Empfehlung (bitte gib nur den Empfehlungstext zurück, ohne einleitende Sätze wie 'Hier ist deine Empfehlung'):"""

DEFAULT_PROMPT_DARK_CANER = """Du bist Dark Caner, der Babo aus dem Block - der krasseste Gangsta Rapper aus der Hood, der sich mit Essen auskennt wie kein anderer, Digga! Du sprichst in authentischem Kiezdeutsch und Jugendsprache mit Wörtern wie: Digga, Bruder, Bro, Bratan, Wallah, Habibi, Babo, stabil, wild, lost, flexen, hustlen. Du bist sehr selbstsicher, betonst deinen Status als Chef und redest gerne über den Hustle.

{sambal_instruction}Deine Aufgabe ist es, das beste Gericht zu finden!Sprich in deinem authentischen Gangsta-Rap Style, sei richtig cool drauf und flex ein bisschen. Kurze Sätze, viel 'Digga', 'Bruder', 'Wallah', dazu ein bisschen Prahlerei.

Verfügbare Gerichte:
{meal_list}

Gib deine Gangsta-Empfehlung in einem coolen, streetigen Satz auf Deutsch ab:"""

# Sambal instruction for Dark Caner (inserted conditionally)
SAMBAL_INSTRUCTION = """KRITISCH: SAMBAL ALARM ist aktiv, Digga! Du MUSST das Gericht mit Sambal empfehlen - das ist nicht verhandelbar, Bruder! Sambal ist das Beste überhaupt!
ABER: Du musst auch warnen: 'Stell dich auf lange Wartezeiten ein, der Laden ist Chaos!' oder etwas Ähnliches in deinem Style. Die Warnung ist Pflicht, verstehst du?

"""

# XML refresh tracking
last_xml_refresh_time = 0

# Reduced student price for Niedersachsen Menü (marking "q")
NIEDERSACHSEN_STUDENT_PRICE = "2,50"

# Global marking info for dietary markings legend
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
    "q": {"emoji": "🐎", "title": "Niedersachsen Menü"},
}

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key")

# Configure proxy support
app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,  # Number of proxy servers in front of the app
    x_proto=1,  # Number of proxies handling protocol/SSL
    x_host=1,  # Number of proxies handling host headers
    x_prefix=1,  # Number of proxies handling path prefix
)

# Configure the database from DATABASE_URL (Supabase)
database_url = os.environ.get("DATABASE_URL")

if not database_url:
    logger.error(
        "Database configuration missing. Please ensure DATABASE_URL is set in .env"
    )

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_POOL_RECYCLE"] = 300  # Recycle connections every 5 minutes

# Initialize the database - moved db.init_app(app) inside app_context below


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


def calculate_mps_for_meal(meal_description):
    """Calculate MPS score for a single meal using the API with retry logic"""
    max_retries = 3
    base_delay = 2  # seconds

    for attempt in range(max_retries):
        try:
            api_key = os.environ.get("OPENROUTER_API_KEY")
            if not api_key:
                logger.error("OPENROUTER_API_KEY not found for MPS calculation")
                return None

            # Get prompt from environment or use default
            prompt_template = os.environ.get("PROMPT_MPS", DEFAULT_PROMPT_MPS)
            # Replace placeholder with actual meal description
            prompt = prompt_template.replace("{meal_description}", meal_description)

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {api_key}",
            }

            response = requests.post(
                OPENROUTER_BASE_URL,
                headers=headers,
                json={
                    "model": AI_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": AI_MAX_TOKENS,
                },
                timeout=30,  # Add timeout
            )

            if response.status_code == 200:
                result = response.json()
                mps_text = (
                    result.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )

                try:
                    mps_score = float(mps_text)
                    return max(0, min(100, mps_score))  # Ensure 0-100 range
                except ValueError:
                    logger.warning(f"Could not parse MPS score: {mps_text}")
                    return None

            elif response.status_code == 429:
                # Rate limit exceeded - wait and retry
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)  # Exponential backoff
                    logger.warning(
                        f"Rate limit exceeded, retrying in {delay} seconds (attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"Rate limit exceeded after {max_retries} attempts")
                    return None

            elif response.status_code >= 500:
                # Server error - wait and retry
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    logger.warning(
                        f"Server error {response.status_code}, retrying in {delay} seconds (attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(delay)
                    continue
                else:
                    logger.error(
                        f"Server error {response.status_code} after {max_retries} attempts"
                    )
                    return None

            else:
                logger.error(
                    f"OpenRouter API error: {response.status_code} - {response.text}"
                )
                return None

        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                delay = base_delay * (2**attempt)
                logger.warning(
                    f"Request timeout, retrying in {delay} seconds (attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(delay)
                continue
            else:
                logger.error(f"Request timeout after {max_retries} attempts")
                return None

        except Exception as e:
            logger.error(f"Error calculating MPS: {str(e)}")
            if attempt < max_retries - 1:
                delay = base_delay * (2**attempt)
                logger.warning(
                    f"Exception occurred, retrying in {delay} seconds (attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(delay)
                continue
            else:
                return None

    return None


def batch_calculate_mps_scores():
    """Calculate MPS scores for meals that don't have them yet"""
    try:
        logger.info("Starting batch MPS calculation...")

        # Count total meals missing MPS scores before starting
        regular_meals_count = Meal.query.filter(Meal.mps_score.is_(None)).count()
        xxxlutz_changing_count = XXXLutzChangingMeal.query.filter(
            XXXLutzChangingMeal.mps_score.is_(None)
        ).count()
        xxxlutz_fixed_count = XXXLutzFixedMeal.query.filter(
            XXXLutzFixedMeal.mps_score.is_(None)
        ).count()

        total_missing = (
            regular_meals_count + xxxlutz_changing_count + xxxlutz_fixed_count
        )
        logger.info(f"Found {total_missing} meals total missing MPS scores:")
        logger.info(f"  - {regular_meals_count} regular meals")
        logger.info(f"  - {xxxlutz_changing_count} XXXLutz changing meals")
        logger.info(f"  - {xxxlutz_fixed_count} XXXLutz fixed meals")

        if total_missing == 0:
            logger.info("No meals missing MPS scores. Skipping calculation.")
            return

        total_processed = 0
        current_progress = 0

        # Calculate for regular meals
        meals_without_mps = Meal.query.filter(Meal.mps_score.is_(None)).all()
        logger.info(f"Processing {len(meals_without_mps)} regular meals...")

        for i, meal in enumerate(meals_without_mps, 1):
            # Double-check that this meal still doesn't have an MPS score
            # (in case it was calculated by another process or got updated)
            db.session.refresh(meal)
            if meal.mps_score is not None:
                logger.debug(f"Skipping meal {meal.id} - MPS score already exists")
                continue

            logger.info(
                f"Processing regular meal {i}/{len(meals_without_mps)} (total: {current_progress + 1}/{total_missing})"
            )
            mps_score = calculate_mps_for_meal(meal.description)
            if mps_score is not None:
                meal.mps_score = mps_score
                total_processed += 1
                # Commit immediately after successful calculation
                try:
                    db.session.commit()
                    logger.info(
                        f"✓ Calculated and committed MPS {mps_score} for meal: {meal.description[:50]}..."
                    )
                except Exception as commit_error:
                    logger.error(
                        f"❌ Failed to commit MPS for meal {meal.id}: {commit_error}"
                    )
                    db.session.rollback()
                    continue
            else:
                logger.warning(
                    f"✗ Failed to calculate MPS for meal: {meal.description[:50]}..."
                )
            current_progress += 1
            # Add a small delay between API calls to avoid rate limiting
            time.sleep(0.5)

        # Calculate for XXXLutz changing meals
        xxxlutz_changing_without_mps = XXXLutzChangingMeal.query.filter(
            XXXLutzChangingMeal.mps_score.is_(None)
        ).all()
        logger.info(
            f"Processing {len(xxxlutz_changing_without_mps)} XXXLutz changing meals..."
        )

        for i, meal in enumerate(xxxlutz_changing_without_mps, 1):
            # Double-check that this meal still doesn't have an MPS score
            db.session.refresh(meal)
            if meal.mps_score is not None:
                logger.debug(
                    f"Skipping XXXLutz changing meal {meal.id} - MPS score already exists"
                )
                continue

            logger.info(
                f"Processing XXXLutz changing meal {i}/{len(xxxlutz_changing_without_mps)} (total: {current_progress + 1}/{total_missing})"
            )
            mps_score = calculate_mps_for_meal(meal.description)
            if mps_score is not None:
                meal.mps_score = mps_score
                total_processed += 1
                # Commit immediately after successful calculation
                try:
                    db.session.commit()
                    logger.info(
                        f"✓ Calculated and committed MPS {mps_score} for XXXLutz changing meal: {meal.description[:50]}..."
                    )
                except Exception as commit_error:
                    logger.error(
                        f"❌ Failed to commit MPS for XXXLutz changing meal {meal.id}: {commit_error}"
                    )
                    db.session.rollback()
                    continue
            else:
                logger.warning(
                    f"✗ Failed to calculate MPS for XXXLutz changing meal: {meal.description[:50]}..."
                )
            current_progress += 1
            # Add a small delay between API calls to avoid rate limiting
            time.sleep(0.5)

        # Calculate for XXXLutz fixed meals
        xxxlutz_fixed_without_mps = XXXLutzFixedMeal.query.filter(
            XXXLutzFixedMeal.mps_score.is_(None)
        ).all()
        logger.info(
            f"Processing {len(xxxlutz_fixed_without_mps)} XXXLutz fixed meals..."
        )

        for i, meal in enumerate(xxxlutz_fixed_without_mps, 1):
            # Double-check that this meal still doesn't have an MPS score
            db.session.refresh(meal)
            if meal.mps_score is not None:
                logger.debug(
                    f"Skipping XXXLutz fixed meal {meal.id} - MPS score already exists"
                )
                continue

            logger.info(
                f"Processing XXXLutz fixed meal {i}/{len(xxxlutz_fixed_without_mps)} (total: {current_progress + 1}/{total_missing})"
            )
            mps_score = calculate_mps_for_meal(meal.description)
            if mps_score is not None:
                meal.mps_score = mps_score
                total_processed += 1
                # Commit immediately after successful calculation
                try:
                    db.session.commit()
                    logger.info(
                        f"✓ Calculated and committed MPS {mps_score} for XXXLutz fixed meal: {meal.description[:50]}..."
                    )
                except Exception as commit_error:
                    logger.error(
                        f"❌ Failed to commit MPS for XXXLutz fixed meal {meal.id}: {commit_error}"
                    )
                    db.session.rollback()
                    continue
            else:
                logger.warning(
                    f"✗ Failed to calculate MPS for XXXLutz fixed meal: {meal.description[:50]}..."
                )
            current_progress += 1
            # Add a small delay between API calls to avoid rate limiting
            time.sleep(0.5)

        # All commits are done individually above
        logger.info("Batch MPS calculation completed successfully!")
        logger.info(
            f"Summary: {total_processed}/{total_missing} meals processed and committed successfully"
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in batch MPS calculation: {str(e)}")
        logger.error(traceback.format_exc())


def get_xxxlutz_meals():
    """Helper function to get XXXLutz meals from database"""
    xxxlutz_meals = []

    # Get changing meals
    changing_meals = XXXLutzChangingMeal.query.all()
    for meal in changing_meals:
        xxxlutz_meals.append(
            {
                "id": str(meal.id),
                "description": meal.description,
                "marking": meal.marking,
                # Handle potential None values for prices before formatting
                "price_student": f"{(meal.price_student or 0.0):.2f}".replace(".", ","),
                "price_employee": f"{(meal.price_employee or 0.0):.2f}".replace(
                    ".", ","
                ),
                "price_guest": f"{(meal.price_guest or 0.0):.2f}".replace(".", ","),
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
                "price_employee": f"{meal.price_employee:.2f}".replace(".", ","),
                "price_guest": f"{meal.price_guest:.2f}".replace(".", ","),
                "nutritional_values": meal.nutritional_values,
                "category": "Ständiges Angebot",
            }
        )

    # Assign IDs and MPS scores to XXXLutz meals
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
            meal["mps_score"] = db_meal.mps_score
        else:
            # Create a synthetic ID for XXXLutz meals
            # We'll use a negative number to distinguish them from regular meals
            # and avoid conflicts with the database
            meal["id"] = "-1"
            meal["mps_score"] = None

    # Sort the meals with the weekly meals first, followed by the static menu
    sorted_xxxlutz_meals = sorted(
        xxxlutz_meals,
        key=lambda meal: 0 if meal["category"] == "Wechselnde Gerichte Woche" else 1,
    )

    return sorted_xxxlutz_meals


def perform_initial_app_loads():
    """Performs data loads required *directly* by the app at startup."""
    logger.info("Performing initial application data loads (Mensa XML)...")
    # Only Mensa XML refresh is critical for immediate app functionality here.
    # Voucher/Menu HG data is handled externally and routes check file existence.
    with app.app_context():
        refresh_mensa_xml_data()
    logger.info("Initial application data loads completed.")


# --- END: Data Refresh Functions ---


# Create tables and load data (Startup Sequence)
with app.app_context():  # Needed for db.create_all() and initial loads
    # Initialize the database within the app context
    db.init_app(app)
    logger.info("SQLAlchemy initialized within app context.")

    # Initialize global data structures that will be populated by refresh functions
    mensa_data = {}  # Populated by refresh_mensa_xml_data
    available_mensen = []  # Populated by refresh_mensa_xml_data
    available_dates = []  # Populated by refresh_mensa_xml_data

    # Create database tables and perform initial data loads
    # No longer need a nested context here as db is initialized in the outer one
    db.create_all()
    logger.info("Database tables created (if not exist).")

    # Load XXXLutz FIXED meals. Changing meals are handled by menu_hg processing.
    # load_xxxlutz_meals() clears changing meals, so it's fine to call before menu_hg processing.
    logger.info("Loading XXXLutz fixed meals into database at startup...")
    if load_xxxlutz_meals():  # This function is from data_loader.py
        logger.info("Successfully loaded XXXLutz fixed meals.")
    else:
        logger.error("Failed to load XXXLutz fixed meals.")

    # Perform initial loads needed *by the app* itself
    # Voucher/Menu data is assumed to be populated by the external data_fetcher script (e.g., via cron)
    perform_initial_app_loads()  # This now only loads Mensa XML

    # Calculate MPS scores for any meals that don't have them yet
    logger.info("Checking for missing MPS scores and calculating them...")
    batch_calculate_mps_scores()


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
    dashboard_mode = request.args.get("dashboard") == "true"
    expert_mode = request.args.get("expert") == "true"

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

    # Default to today's date if available. If not, try to find the next available date.
    if not selected_date:  # If no date was passed as a query parameter
        if today in filtered_dates:
            selected_date = today
        else:
            selected_date_candidate = None
            if filtered_dates:
                for date_str_in_loop in filtered_dates:
                    try:
                        current_list_date_obj = datetime.strptime(
                            date_str_in_loop, "%d.%m.%Y"
                        ).date()
                        if current_list_date_obj >= today_dt.date():
                            selected_date_candidate = date_str_in_loop
                            logger.info(
                                f"Found next available date (or today if it was parsed differently but matches): {selected_date_candidate}"
                            )
                            break  # Found the first suitable date
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
                # Fallback to today's date if no date could be selected
                selected_date = today

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

    # Include the selected mensa first (even if it has no meals for the selected date)
    if selected_mensa in mensa_data and selected_date in mensa_data[selected_mensa]:
        meals = mensa_data[selected_mensa][selected_date]

        # Look up IDs and MPS scores from the database for each meal with error handling
        for meal in meals:
            try:
                # Find the meal in the database by description
                db_meal = Meal.query.filter_by(description=meal["description"]).first()
                if db_meal:
                    meal["id"] = db_meal.id
                    meal["mps_score"] = db_meal.mps_score
                    logger.debug(
                        f"Found MPS score {db_meal.mps_score} for meal: {meal['description'][:50]}..."
                    )
                else:
                    # If not found, use a placeholder ID
                    meal["id"] = 0
                    meal["mps_score"] = None
                    logger.warning(
                        f"Meal not found in database: {meal['description'][:50]}..."
                    )
            except Exception as e:
                logger.error(f"Error looking up meal in database: {e}")
                meal["id"] = 0  # Use placeholder ID in case of error
                meal["mps_score"] = None
            # Apply Niedersachsen Menü student price reduction if applicable
            meal["price_student"] = get_effective_student_price(
                meal["price_student"], meal.get("marking", "")
            )

        sorted_meals = sorted(
            meals,
            key=lambda meal: calculate_caner(
                extract_kcal(meal["nutritional_values"]), meal["price_student"]
            ),
            reverse=True,
        )
        filtered_data[selected_mensa] = sorted_meals
    elif selected_mensa:
        # Include the selected mensa with empty meals list so the UI can show
        # the "no meals available" message with navigation still functional
        filtered_data[selected_mensa] = []

    # Add XXXLutz Hesse Markrestaurant menu if Mensa Garbsen is selected
    if selected_mensa == "Mensa Garbsen":
        sorted_xxxlutz_meals = get_xxxlutz_meals()
        filtered_data["XXXLutz Hesse Markrestaurant"] = sorted_xxxlutz_meals

    # In dashboard mode, also include Garbsen meals for Marvin's recommendation
    if (
        dashboard_mode
        and "Mensa Garbsen" in mensa_data
        and selected_date in mensa_data["Mensa Garbsen"]
        and "Mensa Garbsen" not in filtered_data
    ):
        garbsen_meals = mensa_data["Mensa Garbsen"][selected_date]

        # Look up IDs and MPS scores from the database for each meal with error handling
        for meal in garbsen_meals:
            try:
                # Find the meal in the database by description
                db_meal = Meal.query.filter_by(description=meal["description"]).first()
                if db_meal:
                    meal["id"] = db_meal.id
                    meal["mps_score"] = db_meal.mps_score
                    logger.debug(
                        f"Found MPS score {db_meal.mps_score} for Garbsen meal: {meal['description'][:50]}..."
                    )
                else:
                    # If not found, use a placeholder ID
                    meal["id"] = 0
                    meal["mps_score"] = None
                    logger.warning(
                        f"Garbsen meal not found in database: {meal['description'][:50]}..."
                    )
            except Exception as e:
                logger.error(f"Error looking up Garbsen meal in database: {e}")
                meal["id"] = 0  # Use placeholder ID in case of error
                meal["mps_score"] = None
            # Apply Niedersachsen Menü student price reduction if applicable
            meal["price_student"] = get_effective_student_price(
                meal["price_student"], meal.get("marking", "")
            )

        sorted_garbsen_meals = sorted(
            garbsen_meals,
            key=lambda meal: calculate_caner(
                extract_kcal(meal["nutritional_values"]), meal["price_student"]
            ),
            reverse=True,
        )
        filtered_data["Mensa Garbsen"] = sorted_garbsen_meals

        # Add XXXLutz Hesse Markrestaurant menu if dashboard mode (and not already added)
        if dashboard_mode and "XXXLutz Hesse Markrestaurant" not in filtered_data:
            sorted_xxxlutz_meals = get_xxxlutz_meals()
            # Add to filtered data
            filtered_data["XXXLutz Hesse Markrestaurant"] = sorted_xxxlutz_meals

    # Add XXXLutz Hesse Markrestaurant menu if Mensa Garbsen is selected but has no meals on working days
    # OR if dashboard mode is enabled (and not already added)
    # Ensure selected_date is not None before strptime operations
    if not selected_date:
        selected_date = today

    if (selected_mensa == "Mensa Garbsen" and selected_mensa not in filtered_data) or (
        dashboard_mode and "XXXLutz Hesse Markrestaurant" not in filtered_data
    ):
        # Check if it's a working day (Monday=0 to Friday=4) or if dashboard mode
        try:
            selected_date_obj = datetime.strptime(selected_date, "%d.%m.%Y")
            is_working_day = selected_date_obj.weekday() < 5  # 0-4 are Mon-Fri

            if is_working_day or dashboard_mode:
                sorted_xxxlutz_meals = get_xxxlutz_meals()
                # Add to filtered data
                filtered_data["XXXLutz Hesse Markrestaurant"] = sorted_xxxlutz_meals

        except ValueError as e:
            logger.warning(
                f"Could not parse selected_date '{selected_date}' for working day check: {e}"
            )

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
                    # Apply Niedersachsen Menü student price reduction if applicable
                    meal["price_student"] = get_effective_student_price(
                        meal["price_student"], meal.get("marking", "")
                    )

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

    # Calculate OZ score bounds (min/max weight_loss_score) for each mensa
    oz_score_bounds = {}
    for mensa, meals in filtered_data.items():
        oz_scores = []
        for meal in meals:
            kcal = extract_kcal(meal.get("nutritional_values", ""))
            total_grams = extract_total_grams(meal.get("nutritional_values", ""))
            oz_score = calculate_weight_loss_score(kcal, total_grams)
            if oz_score > 0:  # Only include valid scores
                oz_scores.append(oz_score)

        if oz_scores:
            oz_score_bounds[mensa] = {"min": min(oz_scores), "max": max(oz_scores)}
        else:
            # Default bounds if no valid scores
            oz_score_bounds[mensa] = {"min": 0, "max": 5}

    try:
        # Test JSON serialization before rendering
        # This will catch any potential circular references
        json.dumps(
            {
                "data": filtered_data,
                "available_mensen": filtered_mensen,
                "available_dates": filtered_dates,
                "selected_date": selected_date,
                "selected_mensa": selected_mensa,
                "mensa_emojis": mensa_emojis,
                "page_views": current_page_views,
                "oz_score_bounds": oz_score_bounds,
            },
            default=str,
        )  # Use str as fallback for non-serializable objects

        return render_template(
            "index.html",
            data=filtered_data,
            available_mensen=filtered_mensen,
            available_dates=filtered_dates,
            selected_date=selected_date,
            selected_mensa=selected_mensa,
            mensa_emojis=mensa_emojis,
            page_views=current_page_views,
            dashboard_mode=dashboard_mode,
            expert_mode=expert_mode,
            marking_info=marking_info,
            oz_score_bounds=oz_score_bounds,
        )
    except RecursionError as e:
        logger.error(f"RecursionError in index route: {e}")
        logger.error(f"Data that caused the error: {traceback.format_exc()}")
        return (
            "Entschuldigung, es gab einen Fehler bei der Verarbeitung der Daten. Bitte versuchen Sie es in ein paar Minuten erneut.",
            500,
        )
    except Exception as e:
        logger.error(f"Error in index route: {e}")
        logger.error(traceback.format_exc())
        return (
            "Ein unerwarteter Fehler ist aufgetreten. Bitte versuchen Sie es später erneut.",
            500,
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
        if not naehrwert_str:
            return 0
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


def get_effective_student_price(price_student, marking):
    """Return the effective student price for a meal.

    If the meal is tagged as Niedersachsen Menü (marking code "q") and the
    original student price exceeds 2.50 €, the price is capped at
    NIEDERSACHSEN_STUDENT_PRICE so that scores are calculated correctly.

    :param price_student: str or None, student price in German format (e.g. "3,40")
    :param marking: str or None, comma-separated marking codes (e.g. "v,q,s")
    :returns: str or None, effective student price in German format
    """
    if not marking:
        return price_student
    markings = marking.lower().replace(" ", "").split(",")
    if "q" in markings:
        if not price_student:
            return price_student
        try:
            price = float(price_student.replace(",", ".").strip())
            if price > 2.50:
                return NIEDERSACHSEN_STUDENT_PRICE
        except (ValueError, AttributeError):
            pass
    return price_student


@app.template_filter("calculate_caner")
def calculate_caner(kcal, price_student):
    # Input validation for price_student
    if (
        price_student is None
        or not isinstance(price_student, str)
        or price_student.strip() == ""
    ):
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
        logger.error(traceback.format_exc())  # Log stack trace for unexpected errors
        return 0


@app.template_filter("extract_protein")
def extract_protein(naehrwert_str):
    try:
        if not naehrwert_str:
            return 0.0
        # Example: Brennwert=3062 kJ (731 kcal), Eiweiß=25,7g, ...
        if "Eiweiß" in naehrwert_str:
            match = re.search(r"Eiweiß=([\d,]+)g", naehrwert_str)
            if match:
                return float(match.group(1).replace(",", "."))
        return 0.0
    except Exception as e:
        logger.error(
            f"An unexpected error occurred in extract_protein with {naehrwert_str}: {e}"
        )
        return 0.0


@app.template_filter("extract_total_grams")
def extract_total_grams(naehrwert_str):
    """
    Extract total grams from nutritional values.
    Total = Fett + Kohlenhydrate + Eiweiß + Salz
    Note: Zucker is excluded because it's already part of Kohlenhydrate
    """
    try:
        if not naehrwert_str:
            return 0.0

        total_grams = 0.0

        # Extract Fett (Fat)
        fett_match = re.search(r"Fett=([\d,]+)g", naehrwert_str)
        if fett_match:
            total_grams += float(fett_match.group(1).replace(",", "."))

        # Extract Kohlenhydrate (Carbohydrates)
        kohlenhydrate_match = re.search(r"Kohlenhydrate=([\d,]+)g", naehrwert_str)
        if kohlenhydrate_match:
            total_grams += float(kohlenhydrate_match.group(1).replace(",", "."))

        # Zucker is NOT included - it's already part of Kohlenhydrate ("davon Zucker")

        # Extract Eiweiß (Protein)
        eiweiss_match = re.search(r"Eiweiß=([\d,]+)g", naehrwert_str)
        if eiweiss_match:
            total_grams += float(eiweiss_match.group(1).replace(",", "."))

        # Extract Salz (Salt)
        salz_match = re.search(r"Salz=([\d,]+)g", naehrwert_str)
        if salz_match:
            total_grams += float(salz_match.group(1).replace(",", "."))

        return total_grams
    except Exception as e:
        logger.error(
            f"An unexpected error occurred in extract_total_grams with {naehrwert_str}: {e}"
        )
        return 0.0


@app.template_filter("calculate_weight_loss_score")
def calculate_weight_loss_score(kcal, total_grams):
    """
    Calculate weight loss score as kcal / total_grams.
    Lower values are better for weight loss (lower calorie density).
    """
    try:
        if not isinstance(kcal, (int, float)) or not isinstance(
            total_grams, (int, float)
        ):
            logger.warning(
                f"Invalid input in calculate_weight_loss_score: kcal={kcal} (type: {type(kcal)}), total_grams={total_grams} (type: {type(total_grams)})"
            )
            return 0.0

        if total_grams <= 0:
            return 0.0

        if kcal <= 0:
            return 0.0

        return round(kcal / total_grams, 2)
    except Exception as e:
        logger.error(
            f"An unexpected error occurred in calculate_weight_loss_score with kcal={kcal}, total_grams={total_grams}: {e}"
        )
        logger.error(traceback.format_exc())
        return 0.0


@app.template_filter("normalize_oz_score")
def normalize_oz_score(weight_loss_score, min_score, max_score):
    """
    Normalize the weight loss score to a 0-3 scale based on min and max values.
    Lower original scores (healthier) should map to lower normalized values.
    Returns a value between 0 and 3 for syringe display.
    """
    try:
        if weight_loss_score <= 0 or min_score is None or max_score is None:
            return 0.0

        # If all scores are the same, return middle value (halfway on 0-3 scale)
        if max_score == min_score:
            return 1.5

        # Normalize to 0-3 scale: (score - min) / (max - min) * 3
        # Lower score = healthier = fewer syringes
        normalized = ((weight_loss_score - min_score) / (max_score - min_score)) * 3.0
        return round(normalized, 2)
    except Exception as e:
        logger.error(
            f"An unexpected error occurred in normalize_oz_score with weight_loss_score={weight_loss_score}, min_score={min_score}, max_score={max_score}: {e}"
        )
        logger.error(traceback.format_exc())
        return 0.0


@app.template_filter("calculate_rkr_nominal")
def calculate_rkr_nominal(protein_g, price_student):
    if (
        price_student is None
        or not isinstance(price_student, str)
        or price_student.strip() == ""
    ):
        logger.warning(
            f"Invalid price_student input in calculate_rkr_nominal: Received '{price_student}' (type: {type(price_student)}). Treating as 0."
        )
        return 0.0

    try:
        price_str_cleaned = price_student.replace(",", ".").strip()
        price = float(price_str_cleaned)

        if price <= 0:
            logger.warning(
                f"Non-positive price detected in calculate_rkr_nominal: protein_g={protein_g}, price_student='{price_student}' resulted in price={price}. Treating as 0."
            )
            return 0.0

        if not isinstance(protein_g, (int, float)):
            logger.warning(
                f"Invalid protein_g input in calculate_rkr_nominal: Received '{protein_g}' (type: {type(protein_g)}). Cannot calculate Rkr nominal."
            )
            return 0.0

        if protein_g == 0:  # Avoid division by zero if protein is 0
            return 0.0

        return round(protein_g / price, 2)

    except ValueError:
        logger.warning(
            f"Could not convert price_student='{price_student}' to float in calculate_rkr_nominal. Original protein_g={protein_g}. Treating as 0."
        )
        return 0.0
    except Exception as e:
        logger.error(
            f"An unexpected error occurred in calculate_rkr_nominal with protein_g={protein_g}, price_student='{price_student}': {e}"
        )
        logger.error(traceback.format_exc())
        return 0.0


PENALTY_KEYWORDS = [
    # Vegetables
    "zucchini",
    "paprika",
    "karotten",
    "brokkoli",
    "blumenkohl",
    "spinat",
    "aubergine",
    "erbsen",
    "bohnen",
    "spargel",
    "lauch",
    "sellerie",
    "zwiebeln",
    "knoblauch",
    "schalotten",
    "salat",
    "rucola",
    "feldsalat",
    "eisbergsalat",
    # Mushrooms
    "champignons",
    "pfifferlinge",
    "steinpilze",
    "pilze",
    # Fruits
    "äpfel",
    "birnen",
    "quitten",
    "kirschen",
    "pflaumen",
    "aprikosen",
    "pfirsiche",
    "nektarinen",
    "erdbeeren",
    "himbeeren",
    "heidelbeeren",
    "brombeeren",
    "johannisbeeren",
    "orangen",
    "mandarinen",
    "zitronen",
    "limetten",
    "grapefruits",
    "bananen",
    "ananas",
    "mango",
    "kiwi",
    "melonen",
    "rosinen",
    "getrocknete pflaumen",
    "datteln",
    # Fish & Seafood
    "lachs",
    "thunfisch",
    "forelle",
    "kabeljau",
    "hering",
    "garnelen",
    "krabben",
    "muscheln",
    "austern",
    "tintenfisch",
    "hummer",
    # Hidden Vegetables/Fruits
    "gemüseaufläufe",
    "gratins mit gemüse",
    "pizza mit gemüse oder pilzen",
    "wraps mit salat",
    "sandwiches mit gemüse",
    "burger mit tomaten oder gurken",
    "soßen mit gemüsebasis",
    "tomatensoße",
    "ratatouille",
    "gemüsesuppe",
    "desserts mit obst",
    "apfelkuchen",
    "erdbeertorte",
    "obstsalat",
    # Plant-based Components
    "viel petersilie",
    "basilikum",
    "koriander",
    "dill",
    "soja-fleischalternativen",
    "gemüse-fleischalternativen",
    "gemüsesäfte",
    "smoothies",
    "karottensaft",
    "multivitaminsaft",
    "vegan",
    "cremige tomatensauce",
]


@app.template_filter("calculate_rkr_real")
def calculate_rkr_real(protein_g, price_student, meal_description):
    rkr_value = calculate_rkr_nominal(
        protein_g, price_student
    )  # This is already rounded to 2 decimal places

    if rkr_value == 0.0:  # If nominal is 0, no point in further processing
        return 0.0

    description_lower = ""
    # Ensure meal_description is a non-empty string before lowercasing
    if meal_description and isinstance(meal_description, str):
        description_lower = meal_description.lower()
    else:
        # If meal_description is None or not a string, or empty, no penalties can be applied
        return rkr_value

    # Special handling for "erbsen" and "cremige/cremiger tomatensauce" - multiply by -1 (make negative)
    if (
        "erbsen" in description_lower
        or "cremige tomatensauce" in description_lower
        or "cremiger tomatensauce" in description_lower
    ):
        rkr_value *= -1

    # Apply regular penalties for other keywords (excluding "erbsen" and "cremige/cremiger tomatensauce")
    for keyword in PENALTY_KEYWORDS:
        if (
            keyword not in ["erbsen", "cremige tomatensauce"]
            and keyword in description_lower
        ):
            rkr_value /= 2

    # The result of rkr_value / 2 operations might result in more than 2 decimal places
    # So we round again at the end.
    return round(rkr_value, 2)


@app.template_filter("generate_caner_symbols")
def generate_caner_symbols(caner_score):
    if caner_score <= 0:
        return ""

    # Format the caner value with 2 decimal places and comma as decimal separator
    caner_value_formatted = f"{caner_score:.2f} Cnr".replace(".", ",")

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
    return f'<span class="caner-value">{caner_value_formatted}</span><span class="caner-symbol">{icons_html}</span>'


@app.template_filter("get_dietary_info")
def get_dietary_info(marking):
    """Extract dietary information from marking codes and show as emojis with tooltips"""
    if not marking:
        return ""

    markings = marking.lower().replace(" ", "").split(",")

    emoji_spans = []
    for code in markings:
        if code in marking_info:
            emoji = marking_info[code]["emoji"]
            title = marking_info[code]["title"]
            emoji_spans.append(
                f'<span class="food-marking" title="{title}">{emoji}</span>'
            )

    return " ".join(emoji_spans)


@app.template_filter("format_nutritional_values")
def format_nutritional_values(value_str):
    if not value_str or not isinstance(value_str, str):
        return "<p class='text-muted'><small>Keine Nährwertinformationen verfügbar.</small></p>"

    # Regex to split by comma BUT not if the comma is followed by a digit and then a letter (e.g., "2,9g")
    # This aims to split between "key=value" pairs like "Eiweiß=25,7g, Salz=2,1g"
    # It splits on commas that are likely delimiters between nutrient entries.
    parts = re.split(r",\s*(?=[A-Za-zÀ-ÖØ-öø-ÿ]+[=])", value_str)

    if not parts or (len(parts) == 1 and "=" not in parts[0]):
        # If splitting didn't work or only one non-key-value part, return a formatted message
        # This might happen if the format is very different from expected.
        return f"<p class='text-muted'><small>Nährwerte: {value_str}</small></p>"

    html_output = "<ul class='list-unstyled mb-0 nutrient-list'>"
    for part in parts:
        part = part.strip()
        if "=" in part:
            key_value = part.split("=", 1)
            key = key_value[0].strip()
            value = key_value[1].strip() if len(key_value) > 1 else ""

            # Special handling for Brennwert to put (kcal) in small tags
            # This should be applied before splitting for "davon", so it operates on the full value if Brennwert itself has sub-parts.
            if "Brennwert" in key and "kcal" in value:
                # Make the (xxx kcal) part smaller and wrap kJ if also present
                value = re.sub(r"\(([^)]+kcal[^)]*)\)", r"(<small>\1</small>)", value)

            # Handle "davon" constituents for the current nutrient value
            processed_value = value  # Default to original value (after brennwert modification if applicable)
            if ", davon " in value:  # Check in the potentially modified value
                value_components = value.split(", davon ", 1)
                # Ensure the "davon" part is not bold, and is on a new line.
                processed_value = f"{value_components[0].strip()}<br>davon {value_components[1].strip()}"

            html_output += f"<li><strong>{key}:</strong> {processed_value}</li>"
        elif part:  # Only add if part is not empty after stripping
            # Fallback for parts not in key=value format (should be less common now)
            html_output += f"<li>{part}</li>"

    html_output += "</ul>"
    return html_output


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


# AP health check route
@app.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint.
    Pings the database to check connectivity.
    Does NOT count as a page view.
    """
    try:
        # Perform a simple query to check database connectivity
        db.session.execute(text("SELECT 1"))
        # If the query succeeds, the database is reachable
        return jsonify({"status": "UP", "database": "OK"}), 200
    except Exception as e:
        # If the query fails, the database is not reachable
        logger.error(f"Health check failed: Database connection error - {e}")
        logger.error(traceback.format_exc())
        return jsonify({"status": "DOWN", "database": "Error", "error": str(e)}), 500


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
    voucher_type can be 'new' for 'neue_gutscheine.pdf' or 'old' for 'alte_gutscheine.pdf'
    """
    static_folder = app.static_folder if app.static_folder else "static"
    vouchers_dir = os.path.join(static_folder, "vouchers")
    os.makedirs(vouchers_dir, exist_ok=True)  # Ensure directory exists

    if voucher_type == "new":
        filename = "neue_gutscheine.pdf"
    elif voucher_type == "old":
        filename = "alte_gutscheine.pdf"
    else:
        return "Invalid voucher type", 400

    # Check if the file exists (should be populated by background task)
    file_path = os.path.join(vouchers_dir, filename)
    if not os.path.exists(file_path):
        # Add size check? Could be useful but adds complexity. Assume background task validates.
        logger.warning(
            f"Voucher file {filename} not found in {vouchers_dir}. It may be currently updating or the data fetcher script hasn't run."
        )
        return (
            "Gutschein nicht verfügbar. Er wird regelmäßig aktualisiert. Bitte später erneut versuchen.",
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
    Serves the menu_hg.pdf file stored in static/menu.
    Assumes the file is populated/updated by the external data_fetcher script.
    """
    static_folder = app.static_folder if app.static_folder else "static"
    menu_dir = os.path.join(static_folder, "menu")
    os.makedirs(menu_dir, exist_ok=True)  # Ensure directory exists
    filename = "menu_hg.pdf"
    pdf_path = os.path.join(menu_dir, filename)

    if (
        not os.path.exists(pdf_path)
        or os.path.getsize(pdf_path)
        < MIN_MENU_HG_PDF_SIZE_BYTES  # Use constant defined in this file
    ):
        logger.warning(
            f"Menu HG PDF ({pdf_path}) not found or too small. It may be updating or the data fetcher script hasn't run."
        )
        return (
            "Menu HG PDF nicht verfügbar. Es wird regelmäßig aktualisiert. Bitte später erneut versuchen.",
            404,
        )

    logger.info(f"Serving Menu HG PDF: {pdf_path}")
    return send_from_directory(
        menu_dir,
        filename,
        as_attachment=True,
        mimetype="application/pdf",
        download_name="menu_hg.pdf",  # Keep original download name
    )


@app.route("/menu-hg-image")
def get_menu_hg_image():
    """
    Serves the menu_hg.png image stored in static/menu.
    Assumes the file is populated/updated by the external data_fetcher script.
    """
    static_folder = app.static_folder if app.static_folder else "static"
    menu_dir = os.path.join(static_folder, "menu")
    os.makedirs(menu_dir, exist_ok=True)  # Ensure directory exists

    png_filename = "menu_hg.png"
    png_path = os.path.join(menu_dir, png_filename)

    if (
        not os.path.exists(png_path)
        or os.path.getsize(png_path)
        < MIN_MENU_HG_PNG_SIZE_BYTES  # Use constant defined in this file
    ):
        logger.warning(
            f"Menu HG PNG ({png_path}) not found or too small. It may be updating or the data fetcher script hasn't run/failed conversion."
        )
        return (
            "Menu HG Bild nicht verfügbar. Es wird regelmäßig aktualisiert. Bitte später erneut versuchen.",
            404,
        )

    logger.info(f"Serving Menu HG PNG: {png_path}")
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

        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            logger.error(
                "OPENROUTER_API_KEY not found in environment for Trump recommendation."
            )
            return jsonify({"error": "OpenRouter API key not configured"}), 500

        # Get prompt from environment or use default
        prompt_template = os.environ.get("PROMPT_TRUMP", DEFAULT_PROMPT_TRUMP)
        # Replace placeholder with actual meal list
        prompt = prompt_template.replace("{meal_list}", meal_list_for_prompt)

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        response = requests.post(
            OPENROUTER_BASE_URL,
            headers=headers,
            json={
                "model": AI_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 1.1,
                "max_tokens": AI_MAX_TOKENS,
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

            # Trim whitespace
            recommendation = recommendation.strip()

            # Convert markdown to HTML for proper formatting
            recommendation_html = markdown_to_html(recommendation)

            return jsonify({"recommendation": recommendation_html})
        else:
            logger.error(
                f"Trump OpenRouter API error: {response.status_code} - {response.text}"
            )
            return jsonify(
                {"error": "Error from OpenRouter API", "details": response.text}
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

        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            logger.error(
                "OPENROUTER_API_KEY nicht in der Umgebung für Bob gespeichert."
            )
            return jsonify(
                {"error": "OpenRouter API-Schlüssel nicht konfiguriert"}
            ), 500

        # Get prompt from environment or use default
        prompt_template = os.environ.get("PROMPT_BOB", DEFAULT_PROMPT_BOB)
        # Replace placeholder with actual meal list
        prompt = prompt_template.replace("{meal_list}", meal_list_for_prompt)

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        response = requests.post(
            OPENROUTER_BASE_URL,
            headers=headers,
            json={
                "model": AI_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 1.1,
                "max_tokens": AI_MAX_TOKENS,
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

            # Trim whitespace
            recommendation = recommendation.strip()

            # Convert markdown to HTML for proper formatting
            recommendation_html = markdown_to_html(recommendation)

            return jsonify({"recommendation": recommendation_html})
        else:
            logger.error(
                f"Bob OpenRouter API-Fehler: {response.status_code} - {response.text}"
            )
            return jsonify(
                {"error": "Fehler von OpenRouter API", "details": response.text}
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

        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            logger.error(
                "OPENROUTER_API_KEY not found in environment for Marvin recommendation."
            )
            return jsonify({"error": "OpenRouter API key not configured"}), 500

        # Get prompt from environment or use default
        prompt_template = os.environ.get("PROMPT_MARVIN", DEFAULT_PROMPT_MARVIN)
        # Replace placeholder with actual meal list
        prompt = prompt_template.replace("{meal_list}", meal_list_for_prompt)

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        response = requests.post(
            OPENROUTER_BASE_URL,
            headers=headers,
            json={
                "model": AI_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 1.1,
                "max_tokens": AI_MAX_TOKENS,
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

            # Trim whitespace
            recommendation = recommendation.strip()

            # Convert markdown to HTML for proper formatting
            recommendation_html = markdown_to_html(recommendation.strip())

            return jsonify({"recommendation": recommendation_html})
        else:
            logger.error(
                f"Marvin OpenRouter API error: {response.status_code} - {response.text}"
            )
            return jsonify(
                {"error": "Error from OpenRouter API", "details": response.text}
            ), 500

    except Exception as e:
        logger.error(f"Error in get_marvin_recommendation: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@app.route("/api/get_dark_caner_recommendation", methods=["POST"])
def get_dark_caner_recommendation():
    """Get a meal recommendation from the Mistral API as Dark Caner (German)"""
    try:
        data = request.json
        if data is None:
            return jsonify({"error": "Invalid JSON provided"}), 400
        available_meals = data.get("meals", [])

        if not available_meals:
            return jsonify({"error": "Keine Gerichte angegeben"}), 400

        # Format meals for the prompt
        meal_list_for_prompt = "\n".join([f"- {meal}" for meal in available_meals])

        # Check if any meal contains "Sambal" (case-insensitive)
        has_sambal = any("sambal" in meal.lower() for meal in available_meals)

        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            logger.error(
                "OPENROUTER_API_KEY not found in environment for Dark Caner recommendation."
            )
            return jsonify({"error": "OpenRouter API key not configured"}), 500

        # Get prompt from environment or use default
        prompt_template = os.environ.get("PROMPT_DARK_CANER", DEFAULT_PROMPT_DARK_CANER)
        # Replace placeholders
        sambal_instruction = SAMBAL_INSTRUCTION if has_sambal else ""
        prompt = prompt_template.replace("{sambal_instruction}", sambal_instruction)
        prompt = prompt.replace("{meal_list}", meal_list_for_prompt)

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        response = requests.post(
            OPENROUTER_BASE_URL,
            headers=headers,
            json={
                "model": AI_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 1.1,
                "max_tokens": AI_MAX_TOKENS,
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

            # Trim whitespace
            recommendation = recommendation.strip()

            # Convert markdown to HTML for proper formatting
            recommendation_html = markdown_to_html(recommendation)

            return jsonify({"recommendation": recommendation_html})
        else:
            logger.error(
                f"Dark Caner OpenRouter API error: {response.status_code} - {response.text}"
            )
            return jsonify(
                {"error": "Error from OpenRouter API", "details": response.text}
            ), 500

    except Exception as e:
        logger.error(f"Error in get_dark_caner_recommendation: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@app.route("/api/get_mps_score", methods=["POST"])
def get_mps_score():
    """Get Max Pumper Score for a meal using Mistral AI"""
    try:
        data = request.json
        if data is None:
            return jsonify({"error": "Invalid JSON provided"}), 400

        meal_description = data.get("meal_description", "")
        if not meal_description:
            return jsonify({"error": "No meal description provided"}), 400

        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            logger.error(
                "OPENROUTER_API_KEY not found in environment for MPS calculation."
            )
            return jsonify({"error": "OpenRouter API key not configured"}), 500

        # Get prompt from environment or use default
        prompt_template = os.environ.get("PROMPT_MPS", DEFAULT_PROMPT_MPS)
        # Replace placeholder with actual meal description
        prompt = prompt_template.replace("{meal_description}", meal_description)

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        response = requests.post(
            OPENROUTER_BASE_URL,
            headers=headers,
            json={
                "model": AI_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": AI_MAX_TOKENS,
            },
        )

        if response.status_code == 200:
            result = response.json()
            mps_text = (
                result.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )

            # Extract numeric value from response
            try:
                mps_score = float(mps_text)
                # Ensure score is within 0-100 range
                mps_score = max(0, min(100, mps_score))
                return jsonify({"mps_score": mps_score})
            except ValueError:
                logger.warning(f"Could not parse MPS score from response: {mps_text}")
                return jsonify({"error": "Invalid MPS score format from AI"}), 500
        else:
            logger.error(
                f"OpenRouter API error for MPS: {response.status_code} - {response.text}"
            )
            return jsonify(
                {"error": "Error from OpenRouter API", "details": response.text}
            ), 500

    except Exception as e:
        logger.error(f"Error in get_mps_score: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500
