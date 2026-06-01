import logging
import traceback
from datetime import datetime

from models import Meal, MensaMealOccurrence, db
from utils.xml_parser import dedupe_marking_codes, parse_mensa_data

logger = logging.getLogger(__name__)


def clean_float_str(val_str):
    """
    Clean a string with a numeric value to prepare for conversion to float.
    Handles both German and international number formats.

    Args:
        val_str (str): The string containing a numeric value, e.g. "1.556,00" or "583,00"

    Returns:
        str: A cleaned string ready for float conversion
    """
    if not val_str:
        return "0"
    # First, remove any thousands separators (dots)
    val_str = val_str.replace(".", "")
    # Then replace comma with dot for decimal point
    val_str = val_str.replace(",", ".")
    return val_str


def load_xml_data_to_db(xml_source):
    """
    Parse XML data and load unique meals into the database.
    Uses bulk operations for efficient database access.

    Args:
        xml_source (str): URL or file path to XML data
    """
    import time

    overall_start = time.time()

    try:
        # Parse the XML data
        parse_start = time.time()
        mensa_data = parse_mensa_data(xml_source)
        parse_duration = time.time() - parse_start
        logger.info(f"XML parsing took {parse_duration:.2f} seconds")

        if not mensa_data:
            logger.error("No data was parsed from the XML source")
            return False

        return load_parsed_mensa_data_to_db(mensa_data, overall_start=overall_start)

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error loading XML data to database: {e}")
        # It's helpful to see the stack trace for unexpected errors during loading
        logger.error(traceback.format_exc())
        return False


def load_parsed_mensa_data_to_db(mensa_data, overall_start=None):
    """
    Load already-parsed Mensa XML data into the database.

    This is used by the app refresh path so one XML download/parse can update both
    persistent rows and the in-memory dashboard menu.
    """
    import time

    if overall_start is None:
        overall_start = time.time()

    if not mensa_data:
        logger.error("No parsed Mensa data was provided for database load")
        return False

    try:
        total_mensen = len(mensa_data)
        total_dates = sum(len(dates) for dates in mensa_data.values())
        total_menu_items = sum(
            len(meals) for dates in mensa_data.values() for meals in dates.values()
        )
        logger.info(
            "Preparing database load for parsed Mensa XML: %s mensen, %s dates, %s menu items",
            total_mensen,
            total_dates,
            total_menu_items,
        )

        # Bulk fetch all existing meals to avoid N+1 queries
        # Build a lookup dictionary: description -> meal_id
        logger.info("Fetching existing meals from database...")
        all_meals = Meal.query.all()
        meal_lookup = {meal.description: meal.id for meal in all_meals}
        meal_by_description = {meal.description: meal for meal in all_meals}
        logger.info(f"Found {len(meal_lookup)} existing meals in database")

        # Bulk fetch all existing occurrences to avoid N+1 queries
        # Build a lookup dictionary: (meal_id, mensa_name, date) -> True
        logger.info("Fetching existing meal occurrences from database...")
        all_occurrences = MensaMealOccurrence.query.all()
        occurrence_lookup = {
            (occ.meal_id, occ.mensa_name, occ.date): True for occ in all_occurrences
        }
        logger.info(f"Found {len(occurrence_lookup)} existing meal occurrences")

        # Track stats for logging
        created_meal_count = 0
        reused_meal_count = 0
        skipped_empty_description_count = 0
        invalid_date_count = 0
        created_occurrence_count = 0
        existing_occurrence_count = 0
        updated_meal_marking_count = 0

        # Collect new meals and occurrences for bulk insert
        new_meals = []
        new_occurrences = []

        # Loop through each mensa and date to find unique meals
        for mensa_name, dates in mensa_data.items():
            mensa_menu_items = sum(len(meals) for meals in dates.values())
            logger.info(
                "Loading mensa '%s' into database: %s dates, %s menu items",
                mensa_name,
                len(dates),
                mensa_menu_items,
            )
            for date_str, meals in dates.items():
                # Convert date string to date object
                try:
                    date_obj = datetime.strptime(date_str, "%d.%m.%Y").date()
                except ValueError:
                    invalid_date_count += 1
                    logger.warning(f"Skipping invalid date: {date_str}")
                    continue

                # Process each meal
                for meal_data in meals:
                    description = meal_data.get("description", "")
                    if not description:
                        skipped_empty_description_count += 1
                        continue
                    marking = dedupe_marking_codes(meal_data.get("marking", ""))

                    # Check if meal exists using lookup dictionary (O(1) instead of DB query)
                    meal_id = meal_lookup.get(description)

                    if meal_id is None:
                        # Create a new meal record
                        try:
                            # Extract CO2 and water values as floats
                            co2_value = (
                                float(clean_float_str(meal_data.get("co2_value", "0")))
                                if meal_data.get("co2_value")
                                else None
                            )
                            co2_savings = (
                                float(
                                    clean_float_str(meal_data.get("co2_savings", "0"))
                                )
                                if meal_data.get("co2_savings")
                                else None
                            )
                            water_value = (
                                float(
                                    clean_float_str(meal_data.get("water_value", "0"))
                                )
                                if meal_data.get("water_value")
                                else None
                            )

                            # Create new meal object (but don't add to session yet)
                            new_meal = Meal(
                                description=description,
                                category=meal_data.get("category", ""),
                                marking=marking,
                                nutritional_values=meal_data.get(
                                    "nutritional_values", ""
                                ),
                                co2_value=co2_value,
                                co2_rating=meal_data.get("co2_rating", ""),
                                co2_savings=co2_savings,
                                water_value=water_value,
                                water_rating=meal_data.get("water_rating", ""),
                                animal_welfare=meal_data.get("animal_welfare", ""),
                                rainforest=meal_data.get("rainforest", ""),
                            )
                            new_meals.append(new_meal)
                            created_meal_count += 1

                        except Exception as e:
                            logger.error(f"Error creating meal '{description}': {e}")
                            continue
                    else:
                        # Meal already exists, use existing ID
                        reused_meal_count += 1
                        existing_meal = meal_by_description.get(description)
                        if existing_meal:
                            existing_marking = existing_meal.marking or ""
                            normalized_existing_marking = dedupe_marking_codes(
                                existing_marking
                            )
                            if existing_marking != normalized_existing_marking:
                                existing_meal.marking = normalized_existing_marking
                                updated_meal_marking_count += 1

                    # Process occurrence after we have meal_id (either from existing or new meal)
                    # For new meals, we need to flush to get the ID
                    if meal_id is None and new_meals:
                        # Flush new meals to get their IDs
                        db.session.add_all(new_meals)
                        db.session.flush()
                        # Update lookup with new meal IDs
                        for new_m in new_meals:
                            meal_lookup[new_m.description] = new_m.id
                            meal_by_description[new_m.description] = new_m
                        # Get the ID for the current meal
                        meal_id = meal_lookup.get(description)
                        new_meals = []  # Reset for next batch

                    # Check if occurrence exists using lookup dictionary
                    if meal_id is not None:
                        occurrence_key = (meal_id, mensa_name, date_obj)
                        if occurrence_key not in occurrence_lookup:
                            try:
                                # Convert prices to float
                                price_student = float(
                                    clean_float_str(
                                        meal_data.get("price_student", "0,00")
                                    )
                                )
                                price_employee = float(
                                    clean_float_str(
                                        meal_data.get("price_employee", "0,00")
                                    )
                                )
                                price_guest = float(
                                    clean_float_str(
                                        meal_data.get("price_guest", "0,00")
                                    )
                                )
                                price_student_card = float(
                                    clean_float_str(
                                        meal_data.get("price_student_card", "0,00")
                                    )
                                )
                                price_employee_card = float(
                                    clean_float_str(
                                        meal_data.get("price_employee_card", "0,00")
                                    )
                                )
                                price_guest_card = float(
                                    clean_float_str(
                                        meal_data.get("price_guest_card", "0,00")
                                    )
                                )

                                new_occurrence = MensaMealOccurrence(
                                    meal_id=meal_id,
                                    mensa_name=mensa_name,
                                    date=date_obj,
                                    price_student=price_student,
                                    price_employee=price_employee,
                                    price_guest=price_guest,
                                    price_student_card=price_student_card,
                                    price_employee_card=price_employee_card,
                                    price_guest_card=price_guest_card,
                                    notes=meal_data.get("notes", ""),
                                )
                                new_occurrences.append(new_occurrence)
                                occurrence_lookup[occurrence_key] = True
                                created_occurrence_count += 1

                            except Exception as e:
                                logger.error(
                                    f"Error creating meal occurrence for '{description}' at {mensa_name} on {date_str}: {e}"
                                )
                        else:
                            existing_occurrence_count += 1

        # Handle any remaining new meals
        if new_meals:
            db.session.add_all(new_meals)
            db.session.flush()
            for new_m in new_meals:
                meal_lookup[new_m.description] = new_m.id
                meal_by_description[new_m.description] = new_m

        # Bulk insert new occurrences
        if new_occurrences:
            db.session.add_all(new_occurrences)

        # Commit all changes to the database
        db.session.commit()

        overall_duration = time.time() - overall_start
        logger.info(
            "Successfully loaded XML data to database: new_meals=%s existing_meals=%s updated_meal_markings=%s new_occurrences=%s existing_occurrences=%s skipped_empty_descriptions=%s invalid_dates=%s",
            created_meal_count,
            reused_meal_count,
            updated_meal_marking_count,
            created_occurrence_count,
            existing_occurrence_count,
            skipped_empty_description_count,
            invalid_date_count,
        )
        logger.info(
            f"Total parsed Mensa database load duration: {overall_duration:.2f} seconds"
        )

        return True

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error loading XML data to database: {e}")
        # It's helpful to see the stack trace for unexpected errors during loading
        logger.error(traceback.format_exc())
        return False
