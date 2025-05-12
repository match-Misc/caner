import logging
import traceback # Added for consistent error logging
from datetime import datetime
from models import db, Meal, MensaMealOccurrence, XXXLutzFixedMeal
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
    val_str = val_str.replace('.', '')
    # Then replace comma with dot for decimal point
    val_str = val_str.replace(',', '.')
    return val_str

def load_xml_data_to_db(xml_source):
    """
    Parse XML data and load unique meals into the database
    
    Args:
        xml_source (str): URL or file path to XML data
    """
    try:
        # Parse the XML data
        mensa_data = parse_mensa_data(xml_source)
        if not mensa_data:
            logger.error("No data was parsed from the XML source")
            return False
        
        # Track stats for logging
        meal_count = 0
        occurrence_count = 0
        
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
                    description = meal_data.get('description', '')
                    if not description:
                        continue
                    
                    # Check if this meal already exists in the database
                    existing_meal = Meal.query.filter_by(description=description).first()
                    
                    if not existing_meal:
                        # Create a new meal record
                        try:
                            # Extract CO2 and water values as floats
                            # Handle values with both dots and commas (like "1.556,00" or "583,00")
                                
                            co2_value = float(clean_float_str(meal_data.get('co2_value', '0'))) if meal_data.get('co2_value') else None
                            co2_savings = float(clean_float_str(meal_data.get('co2_savings', '0'))) if meal_data.get('co2_savings') else None
                            water_value = float(clean_float_str(meal_data.get('water_value', '0'))) if meal_data.get('water_value') else None
                            
                            # Create new meal
                            new_meal = Meal()
                            new_meal.description = description
                            new_meal.category = meal_data.get('category', '')
                            new_meal.marking = meal_data.get('marking', '')
                            new_meal.nutritional_values = meal_data.get('nutritional_values', '')
                            new_meal.co2_value = co2_value
                            new_meal.co2_rating = meal_data.get('co2_rating', '')
                            new_meal.co2_savings = co2_savings
                            new_meal.water_value = water_value
                            new_meal.water_rating = meal_data.get('water_rating', '')
                            new_meal.animal_welfare = meal_data.get('animal_welfare', '')
                            new_meal.rainforest = meal_data.get('rainforest', '')
                            db.session.add(new_meal)
                            db.session.flush()  # Get the ID without committing
                            meal_id = new_meal.id
                            meal_count += 1
                            
                        except Exception as e:
                            logger.error(f"Error creating meal '{description}': {e}")
                            continue
                    else:
                        meal_id = existing_meal.id
                    
                    # Create a meal occurrence record (when and where this meal is served)
                    try:
                        # Convert prices to float using the module-level clean_float_str function
                            
                        price_student = float(clean_float_str(meal_data.get('price_student', '0,00')))
                        price_employee = float(clean_float_str(meal_data.get('price_employee', '0,00')))
                        price_guest = float(clean_float_str(meal_data.get('price_guest', '0,00')))
                        price_student_card = float(clean_float_str(meal_data.get('price_student_card', '0,00')))
                        price_employee_card = float(clean_float_str(meal_data.get('price_employee_card', '0,00')))
                        price_guest_card = float(clean_float_str(meal_data.get('price_guest_card', '0,00')))
                        
                        # Check if this occurrence already exists
                        existing_occurrence = MensaMealOccurrence.query.filter_by(
                            meal_id=meal_id,
                            mensa_name=mensa_name,
                            date=date_obj
                        ).first()
                        
                        if not existing_occurrence:
                            new_occurrence = MensaMealOccurrence()
                            new_occurrence.meal_id = meal_id
                            new_occurrence.mensa_name = mensa_name
                            new_occurrence.date = date_obj
                            new_occurrence.price_student = price_student
                            new_occurrence.price_employee = price_employee
                            new_occurrence.price_guest = price_guest
                            new_occurrence.price_student_card = price_student_card
                            new_occurrence.price_employee_card = price_employee_card
                            new_occurrence.price_guest_card = price_guest_card
                            new_occurrence.notes = meal_data.get('notes', '')
                            db.session.add(new_occurrence)
                            occurrence_count += 1
                            
                    except Exception as e:
                        logger.error(f"Error creating meal occurrence for '{description}' at {mensa_name} on {date_str}: {e}")
        
        # Commit all changes to the database
        db.session.commit()
        logger.info(f"Successfully loaded {meal_count} unique meals and {occurrence_count} meal occurrences")
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
                    'description': 'Schnitzel vom Schwein oder Huhn mit Pommes und Ketchup',
                    'marking': 's,g', 'price_student': 9.90, 'price_employee': 10.90, 'price_guest': 11.90,
                    'nutritional_values': 'Brennwert=3200 kJ (760 kcal)',
                },
                {
                    'description': 'Currywurst mit Pommes Frites',
                    'marking': 's', 'price_student': 7.90, 'price_employee': 8.90, 'price_guest': 9.90,
                    'nutritional_values': 'Brennwert=3000 kJ (715 kcal)',
                },
                {
                    'description': 'Käsespätzle mit Bergkäse und Röstzwiebeln',
                    'marking': 'v,26', 'price_student': 8.50, 'price_employee': 9.50, 'price_guest': 10.50,
                    'nutritional_values': 'Brennwert=2900 kJ (690 kcal)',
                },
                {
                    'description': 'Süßkartoffel-Gemüse-Curry-Bowl mit Wildreis und Salat',
                    'marking': 'x', 'price_student': 8.90, 'price_employee': 9.90, 'price_guest': 10.90,
                    'nutritional_values': 'Brennwert=2300 kJ (548 kcal)',
                },
                {
                    'description': 'Veganes Schnitzel mit Pommes Frites',
                    'marking': 'x', 'price_student': 8.90, 'price_employee': 9.90, 'price_guest': 10.90,
                    'nutritional_values': 'Brennwert=2750 kJ (655 kcal)',
                },
                {
                    'description': 'Großer Salatteller mit Briespitzen und Tomate, Gurke',
                    'marking': 'v,26', 'price_student': 7.90, 'price_employee': 8.90, 'price_guest': 9.90,
                    'nutritional_values': 'Brennwert=1500 kJ (358 kcal)',
                },
                {
                    'description': 'Caesar Salatteller mit Hühnerbrustmedaillons und Blattsalat, Tomate, Gurke',
                    'marking': 'g,26,22', 'price_student': 8.90, 'price_employee': 9.90, 'price_guest': 10.90,
                    'nutritional_values': 'Brennwert=1800 kJ (430 kcal)',
                },
                {
                    'description': 'Seelachfilet mit Kartoffelsalat und Remoulade',
                    'marking': 'f,22', 'price_student': 8.90, 'price_employee': 9.90, 'price_guest': 10.90,
                    'nutritional_values': 'Brennwert=2500 kJ (595 kcal)',
                },
                {
                    'description': 'Schweinerückensteaks mit Gemüse und Pommes Frites',
                    'marking': 's', 'price_student': 9.90, 'price_employee': 10.90, 'price_guest': 11.90,
                    'nutritional_values': 'Brennwert=3100 kJ (740 kcal)',
                },
                {
                    'description': 'Spaghetti Bolognese',
                    'marking': 'r,20a', 'price_student': 7.90, 'price_employee': 8.90, 'price_guest': 9.90,
                    'nutritional_values': 'Brennwert=2800 kJ (670 kcal)',
                }
            ]
            for meal_data in fixed_meals_data:
                meal = XXXLutzFixedMeal(
                    description=meal_data['description'],
                    marking=meal_data['marking'],
                    price_student=meal_data['price_student'],
                    price_employee=meal_data['price_employee'],
                    price_guest=meal_data['price_guest'],
                    nutritional_values=meal_data['nutritional_values']
                )
                db.session.add(meal)
            db.session.commit()
            logger.info(f"Successfully seeded {len(fixed_meals_data)} XXXLutz fixed meals.")
        else:
            logger.info("XXXLutzFixedMeal table already populated. Skipping seeding of fixed meals.")

        logger.info("load_xxxlutz_meals: Fixed meals checked/seeded. Changing meals are managed by the AI process in app.py.")
        return True
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in load_xxxlutz_meals: {e}")
        # It's helpful to see the stack trace for unexpected errors during loading
        logger.error(traceback.format_exc())
        return False
