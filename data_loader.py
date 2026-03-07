import logging
import traceback  # Added for consistent error logging
from datetime import datetime

from models import Meal, MensaMealOccurrence, XXXLutzFixedMeal, db
from utils.xml_parser import parse_mensa_data

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

        # Bulk fetch all existing meals to avoid N+1 queries
        # Build a lookup dictionary: description -> meal_id
        logger.info("Fetching existing meals from database...")
        all_meals = Meal.query.all()
        meal_lookup = {meal.description: meal.id for meal in all_meals}
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
        meal_count = 0
        occurrence_count = 0

        # Collect new meals and occurrences for bulk insert
        new_meals = []
        new_occurrences = []

        # Loop through each mensa and date to find unique meals
        for mensa_name, dates in mensa_data.items():
            for date_str, meals in dates.items():
                # Convert date string to date object
                try:
                    date_obj = datetime.strptime(date_str, "%d.%m.%Y").date()
                except ValueError:
                    logger.warning(f"Skipping invalid date: {date_str}")
                    continue

                # Process each meal
                for meal_data in meals:
                    description = meal_data.get("description", "")
                    if not description:
                        continue

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
                                marking=meal_data.get("marking", ""),
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

                        except Exception as e:
                            logger.error(f"Error creating meal '{description}': {e}")
                            continue
                    else:
                        # Meal already exists, use existing ID
                        pass

                    # Process occurrence after we have meal_id (either from existing or new meal)
                    # For new meals, we need to flush to get the ID
                    if meal_id is None and new_meals:
                        # Flush new meals to get their IDs
                        db.session.add_all(new_meals)
                        db.session.flush()
                        # Update lookup with new meal IDs
                        for new_m in new_meals:
                            meal_lookup[new_m.description] = new_m.id
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

                            except Exception as e:
                                logger.error(
                                    f"Error creating meal occurrence for '{description}' at {mensa_name} on {date_str}: {e}"
                                )

        # Handle any remaining new meals
        if new_meals:
            db.session.add_all(new_meals)
            db.session.flush()
            for new_m in new_meals:
                meal_lookup[new_m.description] = new_m.id

        # Bulk insert new occurrences
        if new_occurrences:
            db.session.add_all(new_occurrences)

        # Commit all changes to the database
        db.session.commit()

        # Count the results
        meal_count = len(new_meals) if "new_meals" in dir() else 0
        occurrence_count = len(new_occurrences)

        overall_duration = time.time() - overall_start
        logger.info(
            f"Successfully loaded {meal_count} unique meals and {occurrence_count} meal occurrences"
        )
        logger.info(
            f"Total load_xml_data_to_db duration: {overall_duration:.2f} seconds"
        )

        return True

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error loading XML data to database: {e}")
        # It's helpful to see the stack trace for unexpected errors during loading
        logger.error(traceback.format_exc())
        return False


def load_xxxlutz_meals():
    """
    Load XXXLutz meals into the database.
    - Fixed meals (XXXLutzFixedMeal) are seeded from a hardcoded list if the table is empty.
    - Changing meals (XXXLutzChangingMeal) are NO LONGER managed here;
      they are updated by the AI process from the menu image (in app.py).
    """
    try:
        # Handle Fixed Meals: Seed only if the table is empty
        if XXXLutzFixedMeal.query.count() == 0:
            logger.info("XXXLutzFixedMeal table is empty. Seeding fixed meals...")
            fixed_meals_data = [
                {
                    "description": "Schnitzel vom Schwein oder Huhn mit Pommes und Ketchup",
                    "marking": "s,g",
                    "price_student": 9.90,
                    "price_employee": 10.90,
                    "price_guest": 11.90,
                    "nutritional_values": "Brennwert=3200 kJ (760 kcal)",
                },
                {
                    "description": "Currywurst mit Pommes Frites",
                    "marking": "s",
                    "price_student": 7.90,
                    "price_employee": 8.90,
                    "price_guest": 9.90,
                    "nutritional_values": "Brennwert=3000 kJ (715 kcal)",
                },
                {
                    "description": "Käsespätzle mit Bergkäse und Röstzwiebeln",
                    "marking": "v,26",
                    "price_student": 8.50,
                    "price_employee": 9.50,
                    "price_guest": 10.50,
                    "nutritional_values": "Brennwert=2900 kJ (690 kcal)",
                },
                {
                    "description": "Süßkartoffel-Gemüse-Curry-Bowl mit Wildreis und Salat",
                    "marking": "x",
                    "price_student": 8.90,
                    "price_employee": 9.90,
                    "price_guest": 10.90,
                    "nutritional_values": "Brennwert=2300 kJ (548 kcal)",
                },
                {
                    "description": "Veganes Schnitzel mit Pommes Frites",
                    "marking": "x",
                    "price_student": 8.90,
                    "price_employee": 9.90,
                    "price_guest": 10.90,
                    "nutritional_values": "Brennwert=2750 kJ (655 kcal)",
                },
                {
                    "description": "Großer Salatteller mit Briespitzen und Tomate, Gurke",
                    "marking": "v,26",
                    "price_student": 7.90,
                    "price_employee": 8.90,
                    "price_guest": 9.90,
                    "nutritional_values": "Brennwert=1500 kJ (358 kcal)",
                },
                {
                    "description": "Caesar Salatteller mit Hühnerbrustmedaillons und Blattsalat, Tomate, Gurke",
                    "marking": "g,26,22",
                    "price_student": 8.90,
                    "price_employee": 9.90,
                    "price_guest": 10.90,
                    "nutritional_values": "Brennwert=1800 kJ (430 kcal)",
                },
                {
                    "description": "Seelachfilet mit Kartoffelsalat und Remoulade",
                    "marking": "f,22",
                    "price_student": 8.90,
                    "price_employee": 9.90,
                    "price_guest": 10.90,
                    "nutritional_values": "Brennwert=2500 kJ (595 kcal)",
                },
                {
                    "description": "Schweinerückensteaks mit Gemüse und Pommes Frites",
                    "marking": "s",
                    "price_student": 9.90,
                    "price_employee": 10.90,
                    "price_guest": 11.90,
                    "nutritional_values": "Brennwert=3100 kJ (740 kcal)",
                },
                {
                    "description": "Spaghetti Bolognese",
                    "marking": "r,20a",
                    "price_student": 7.90,
                    "price_employee": 8.90,
                    "price_guest": 9.90,
                    "nutritional_values": "Brennwert=2800 kJ (670 kcal)",
                },
            ]
            for meal_data in fixed_meals_data:
                meal = XXXLutzFixedMeal(
                    description=meal_data["description"],
                    marking=meal_data["marking"],
                    price_student=meal_data["price_student"],
                    price_employee=meal_data["price_employee"],
                    price_guest=meal_data["price_guest"],
                    nutritional_values=meal_data["nutritional_values"],
                )
                db.session.add(meal)
            db.session.commit()
            logger.info(
                f"Successfully seeded {len(fixed_meals_data)} XXXLutz fixed meals."
            )
        else:
            logger.info(
                "XXXLutzFixedMeal table already populated. Skipping seeding of fixed meals."
            )

        logger.info(
            "load_xxxlutz_meals: Fixed meals checked/seeded. Changing meals are managed by the AI process in app.py."
        )
        return True

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in load_xxxlutz_meals: {e}")
        # It's helpful to see the stack trace for unexpected errors during loading
        logger.error(traceback.format_exc())
        return False
