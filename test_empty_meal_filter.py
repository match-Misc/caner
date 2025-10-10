#!/usr/bin/env python3
"""
Test to verify that meals with empty descriptions are filtered out
from the XML parser output.
"""

import sys
import os
import xml.etree.ElementTree as ET

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.xml_parser import parse_mensa_data


def test_empty_description_filtering():
    """Test that meals with empty descriptions are filtered out"""
    
    print("Testing empty meal description filtering...")
    
    # Create test XML with some meals having empty descriptions
    test_xml = '''<?xml version="1.0" encoding="utf-8"?>
<DATAPACKET>
    <ROWDATA>
        <ROW MENSA="Test Mensa" DATUM="15.10.2025" 
             BESCHREIBUNG="Valid Meal 1" 
             PREIS_STUDENT="3,50" 
             NAEHRWERTE="Brennwert=500 kJ"/>
        <ROW MENSA="Test Mensa" DATUM="15.10.2025" 
             BESCHREIBUNG="" 
             PREIS_STUDENT="4,00" 
             NAEHRWERTE="Brennwert=600 kJ"/>
        <ROW MENSA="Test Mensa" DATUM="15.10.2025" 
             BESCHREIBUNG="Valid Meal 2" 
             PREIS_STUDENT="5,50" 
             NAEHRWERTE="Brennwert=700 kJ"/>
        <ROW MENSA="Test Mensa" DATUM="15.10.2025" 
             BESCHREIBUNG="   " 
             PREIS_STUDENT="6,00" 
             NAEHRWERTE="Brennwert=800 kJ"/>
        <ROW MENSA="Test Mensa" DATUM="16.10.2025" 
             BESCHREIBUNG="Valid Meal 3" 
             PREIS_STUDENT="7,00" 
             NAEHRWERTE="Brennwert=900 kJ"/>
    </ROWDATA>
</DATAPACKET>'''
    
    # Save test XML to a temporary file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
        f.write(test_xml)
        temp_file = f.name
    
    try:
        # Parse the XML
        mensa_data = parse_mensa_data(temp_file)
        
        # Verify the structure
        assert "Test Mensa" in mensa_data, "Test Mensa should be in the data"
        
        # Check meals for 15.10.2025
        meals_oct15 = mensa_data["Test Mensa"]["15.10.2025"]
        print(f"Found {len(meals_oct15)} meals for 15.10.2025")
        
        # Should only have 2 valid meals (empty and whitespace-only descriptions filtered out)
        assert len(meals_oct15) == 2, f"Expected 2 meals, got {len(meals_oct15)}"
        
        # Check the descriptions
        descriptions = [meal['description'] for meal in meals_oct15]
        print(f"Meal descriptions: {descriptions}")
        
        assert "Valid Meal 1" in descriptions, "Valid Meal 1 should be present"
        assert "Valid Meal 2" in descriptions, "Valid Meal 2 should be present"
        assert "" not in descriptions, "Empty description should be filtered out"
        assert "   " not in descriptions, "Whitespace-only description should be filtered out"
        
        # Check meals for 16.10.2025
        meals_oct16 = mensa_data["Test Mensa"]["16.10.2025"]
        print(f"Found {len(meals_oct16)} meals for 16.10.2025")
        
        assert len(meals_oct16) == 1, f"Expected 1 meal, got {len(meals_oct16)}"
        assert meals_oct16[0]['description'] == "Valid Meal 3", "Valid Meal 3 should be present"
        
        print("✓ All tests passed! Empty descriptions are properly filtered out.")
        return True
        
    finally:
        # Clean up the temporary file
        os.unlink(temp_file)


def test_all_empty_descriptions():
    """Test that a date with all empty descriptions results in empty list"""
    
    print("\nTesting date with all empty meal descriptions...")
    
    test_xml = '''<?xml version="1.0" encoding="utf-8"?>
<DATAPACKET>
    <ROWDATA>
        <ROW MENSA="Test Mensa" DATUM="20.10.2025" 
             BESCHREIBUNG="" 
             PREIS_STUDENT="3,50"/>
        <ROW MENSA="Test Mensa" DATUM="20.10.2025" 
             BESCHREIBUNG="   " 
             PREIS_STUDENT="4,00"/>
    </ROWDATA>
</DATAPACKET>'''
    
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
        f.write(test_xml)
        temp_file = f.name
    
    try:
        mensa_data = parse_mensa_data(temp_file)
        
        # The date should still exist in the structure, but with an empty list
        assert "Test Mensa" in mensa_data, "Test Mensa should be in the data"
        assert "20.10.2025" in mensa_data["Test Mensa"], "Date should be in the data"
        
        meals = mensa_data["Test Mensa"]["20.10.2025"]
        print(f"Found {len(meals)} meals for date with all empty descriptions")
        
        assert len(meals) == 0, f"Expected 0 meals, got {len(meals)}"
        
        print("✓ Test passed! Date with all empty descriptions has empty meal list.")
        return True
        
    finally:
        os.unlink(temp_file)


if __name__ == "__main__":
    try:
        success = True
        success = test_empty_description_filtering() and success
        success = test_all_empty_descriptions() and success
        
        if success:
            print("\n" + "="*50)
            print("All tests passed successfully!")
            print("="*50)
            sys.exit(0)
        else:
            print("\n" + "="*50)
            print("Some tests failed!")
            print("="*50)
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
