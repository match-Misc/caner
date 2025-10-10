import xml.etree.ElementTree as ET
from datetime import datetime
import requests
import logging # Moved from inside function

def parse_mensa_data(xml_source):
    """
    Parse XML data containing mensa menu information.
    
    Args:
        xml_source (str): Either a local file path or a URL to the XML data.
    
    Returns:
        dict: A nested dictionary structure:
        {
            mensa_name: {
                date: [
                    {meal_data},
                    {meal_data},
                    ...
                ],
                ...
            },
            ...
        }
    """
    logger = logging.getLogger(__name__)
    
    # Create a dictionary to store mensa data
    mensa_data = {}
    
    try:
        # Determine if source is a URL or a local file
        if xml_source.startswith(('http://', 'https://')):
            # Download XML from URL
            response = requests.get(xml_source)
            response.raise_for_status()  # Raise exception for non-200 status codes
            
            # Fix potentially malformed or truncated XML
            xml_content = response.content
            try:
                # Try parsing as is first
                root = ET.fromstring(xml_content)
            except ET.ParseError as xml_error:
                logger.warning(f"XML parsing error: {xml_error}, attempting recovery...")
                
                # Try to fix common XML problems
                xml_text = xml_content.decode('utf-8', errors='ignore')
                
                # Add missing closing tags if needed
                if not xml_text.strip().endswith('</DATAPACKET>'):
                    logger.warning("XML appears to be truncated, fixing closing tags")
                    if '<ROWDATA>' in xml_text and '</ROWDATA>' not in xml_text:
                        xml_text += '</ROWDATA>'
                    xml_text += '</DATAPACKET>'
                
                # Try parsing again with fixed XML
                try:
                    root = ET.fromstring(xml_text.encode('utf-8'))
                except ET.ParseError as recovery_error:
                    logger.error(f"Recovery failed: {recovery_error}")
                    # Try one more approach - extract and parse what we can
                    try:
                        import re
                        # Extract all complete ROW tags
                        row_pattern = r'<ROW[^>]+/>'
                        rows = re.findall(row_pattern, xml_text)
                        
                        # Create a minimal valid XML document
                        minimal_xml = '<?xml version="1.0" encoding="utf-8"?><DATAPACKET><ROWDATA>'
                        for row in rows:
                            minimal_xml += row
                        minimal_xml += '</ROWDATA></DATAPACKET>'
                        
                        root = ET.fromstring(minimal_xml)
                        logger.info(f"Recovered {len(rows)} rows using regex")
                    except Exception as last_error:
                        logger.error(f"All recovery methods failed: {last_error}")
                        raise
        else:
            # Parse from local file
            tree = ET.parse(xml_source)
            root = tree.getroot()
        
        # Find ROWDATA element containing all meal entries
        rowdata = root.find('ROWDATA')
        if rowdata is None:
            logger.warning("No ROWDATA element found in the XML")
            return mensa_data
            
        # Process each ROW element (meal entry)
        for row in rowdata.findall('ROW'):
            mensa_name = row.get('MENSA', 'Unknown')
            date = row.get('DATUM', '')
            
            # Initialize the mensa in the dictionary if not already present
            if mensa_name not in mensa_data:
                mensa_data[mensa_name] = {}
            
            # Initialize the date in the mensa dictionary if not already present
            if date not in mensa_data[mensa_name]:
                mensa_data[mensa_name][date] = []
            
            # Extract meal data
            meal_data = {
                'category': row.get('BEZEICHNUNG_KATEGORIE', ''),
                'description': row.get('BESCHREIBUNG', ''),
                'marking': row.get('KENNZEICHNUNG', ''),
                'price_student': row.get('PREIS_STUDENT', '0,00'),
                'price_employee': row.get('PREIS_BEDIENSTETER', '0,00'),
                'price_guest': row.get('PREIS_GAST', '0,00'),
                'price_student_card': row.get('PREIS_STUDENT_KARTE', '0,00'),
                'price_employee_card': row.get('PREIS_BEDIENSTETER_KARTE', '0,00'),
                'price_guest_card': row.get('PREIS_GAST_KARTE', '0,00'),
                'image_id': row.get('BILD_ID', ''),
                'nutritional_values': row.get('NAEHRWERTE', ''),
                'notes': row.get('HINWEISE', ''),
                'co2_value': row.get('EXTINFO_CO2_WERT', ''),
                'co2_rating': row.get('EXTINFO_CO2_BEWERTUNG', ''),
                'co2_savings': row.get('EXTINFO_CO2_EINSPARUNG', ''),
                'water_value': row.get('EXTINFO_WASSER_WERT', ''),
                'water_rating': row.get('EXTINFO_WASSER_BEWERTUNG', ''),
                'animal_welfare': row.get('EXTINFO_TIERWOHL', ''),
                'rainforest': row.get('EXTINFO_REGENWALD', '')
            }
            
            # Skip meals with empty description
            if not meal_data['description'] or not meal_data['description'].strip():
                logger.debug(f"Skipping meal with empty description at {mensa_name} on {date}")
                continue
            
            # Add the meal data to the corresponding mensa and date
            mensa_data[mensa_name][date].append(meal_data)
        
        return mensa_data
    
    except Exception as e:
        logger.error(f"Error parsing XML file: {e}") # Changed from print to logger.error
        return {}

def get_available_mensen(mensa_data):
    """Get a list of all available mensen from the parsed data."""
    return sorted(list(mensa_data.keys()))

def get_available_dates(mensa_data):
    """Get a list of all available dates from the parsed data."""
    dates = set()
    for mensa in mensa_data.values():
        dates.update(mensa.keys())
    
    # Convert strings to datetime objects for sorting
    date_objs = []
    for date_str in dates:
        try:
            date_obj = datetime.strptime(date_str, "%d.%m.%Y")
            date_objs.append((date_str, date_obj))
        except ValueError:
            # Skip invalid dates
            continue
    
    # Sort by date and return original string format
    sorted_dates = [date_str for date_str, _ in sorted(date_objs, key=lambda x: x[1])]
    return sorted_dates
