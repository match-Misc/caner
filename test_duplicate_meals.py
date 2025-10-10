#!/usr/bin/env python3
"""
Test to verify that duplicate meals are filtered out during XML parsing.
This test ensures that when the XML contains multiple identical meal entries
for the same mensa and date, only one copy is kept.
"""

import sys
import os
import xml.etree.ElementTree as ET

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.xml_parser import parse_mensa_data


def test_duplicate_meals_same_date():
    """Test that duplicate meals on the same date are filtered out"""
    
    print("Testing duplicate meal filtering for same mensa and date...")
    
    # Create test XML with duplicate meals
    test_xml = '''<?xml version="1.0" encoding="utf-8"?>
<DATAPACKET>
    <ROWDATA>
        <ROW MENSA="Hauptmensa" DATUM="15.10.2025" 
             BESCHREIBUNG="Spaghetti Bolognese" 
             BEZEICHNUNG_KATEGORIE="Hauptgericht"
             PREIS_STUDENT="3,50" 
             NAEHRWERTE="Brennwert=500 kJ"/>
        <ROW MENSA="Hauptmensa" DATUM="15.10.2025" 
             BESCHREIBUNG="Caesar Salad" 
             BEZEICHNUNG_KATEGORIE="Salat"
             PREIS_STUDENT="4,00" 
             NAEHRWERTE="Brennwert=300 kJ"/>
        <ROW MENSA="Hauptmensa" DATUM="15.10.2025" 
             BESCHREIBUNG="Spaghetti Bolognese" 
             BEZEICHNUNG_KATEGORIE="Hauptgericht"
             PREIS_STUDENT="3,50" 
             NAEHRWERTE="Brennwert=500 kJ"/>
        <ROW MENSA="Hauptmensa" DATUM="15.10.2025" 
             BESCHREIBUNG="Chicken Curry" 
             BEZEICHNUNG_KATEGORIE="Hauptgericht"
             PREIS_STUDENT="4,50" 
             NAEHRWERTE="Brennwert=600 kJ"/>
        <ROW MENSA="Hauptmensa" DATUM="15.10.2025" 
             BESCHREIBUNG="Caesar Salad" 
             BEZEICHNUNG_KATEGORIE="Salat"
             PREIS_STUDENT="4,00" 
             NAEHRWERTE="Brennwert=300 kJ"/>
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
        assert "Hauptmensa" in mensa_data, "Hauptmensa should be in the data"
        
        # Check meals for 15.10.2025
        meals_oct15 = mensa_data["Hauptmensa"]["15.10.2025"]
        print(f"Found {len(meals_oct15)} meals for 15.10.2025")
        
        # Should only have 3 unique meals (Spaghetti, Caesar Salad, Chicken Curry)
        # even though we had 5 entries (2 duplicates)
        assert len(meals_oct15) == 3, f"Expected 3 unique meals, got {len(meals_oct15)}"
        
        # Check the descriptions
        descriptions = [meal['description'] for meal in meals_oct15]
        print(f"Meal descriptions: {descriptions}")
        
        # Count occurrences of each meal
        description_counts = {}
        for desc in descriptions:
            description_counts[desc] = description_counts.get(desc, 0) + 1
        
        # Each meal should appear exactly once
        for desc, count in description_counts.items():
            assert count == 1, f"Meal '{desc}' appears {count} times, should appear exactly once"
        
        assert "Spaghetti Bolognese" in descriptions, "Spaghetti Bolognese should be present"
        assert "Caesar Salad" in descriptions, "Caesar Salad should be present"
        assert "Chicken Curry" in descriptions, "Chicken Curry should be present"
        
        print("✓ All tests passed! Duplicate meals are properly filtered out.")
        return True
        
    finally:
        # Clean up the temporary file
        os.unlink(temp_file)


def test_duplicates_different_dates():
    """Test that same meal on different dates is NOT filtered out"""
    
    print("\nTesting that same meal on different dates is kept...")
    
    test_xml = '''<?xml version="1.0" encoding="utf-8"?>
<DATAPACKET>
    <ROWDATA>
        <ROW MENSA="Hauptmensa" DATUM="15.10.2025" 
             BESCHREIBUNG="Spaghetti Bolognese" 
             PREIS_STUDENT="3,50"/>
        <ROW MENSA="Hauptmensa" DATUM="16.10.2025" 
             BESCHREIBUNG="Spaghetti Bolognese" 
             PREIS_STUDENT="3,50"/>
        <ROW MENSA="Hauptmensa" DATUM="17.10.2025" 
             BESCHREIBUNG="Spaghetti Bolognese" 
             PREIS_STUDENT="3,50"/>
    </ROWDATA>
</DATAPACKET>'''
    
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
        f.write(test_xml)
        temp_file = f.name
    
    try:
        mensa_data = parse_mensa_data(temp_file)
        
        # Should have the meal on all 3 dates
        assert "Hauptmensa" in mensa_data, "Hauptmensa should be in the data"
        assert "15.10.2025" in mensa_data["Hauptmensa"], "15.10.2025 should be present"
        assert "16.10.2025" in mensa_data["Hauptmensa"], "16.10.2025 should be present"
        assert "17.10.2025" in mensa_data["Hauptmensa"], "17.10.2025 should be present"
        
        assert len(mensa_data["Hauptmensa"]["15.10.2025"]) == 1, "Should have 1 meal on 15.10.2025"
        assert len(mensa_data["Hauptmensa"]["16.10.2025"]) == 1, "Should have 1 meal on 16.10.2025"
        assert len(mensa_data["Hauptmensa"]["17.10.2025"]) == 1, "Should have 1 meal on 17.10.2025"
        
        print("✓ Test passed! Same meal on different dates is correctly kept.")
        return True
        
    finally:
        os.unlink(temp_file)


def test_duplicates_different_mensas():
    """Test that same meal at different mensas is NOT filtered out"""
    
    print("\nTesting that same meal at different mensas is kept...")
    
    test_xml = '''<?xml version="1.0" encoding="utf-8"?>
<DATAPACKET>
    <ROWDATA>
        <ROW MENSA="Hauptmensa" DATUM="15.10.2025" 
             BESCHREIBUNG="Spaghetti Bolognese" 
             PREIS_STUDENT="3,50"/>
        <ROW MENSA="Contine" DATUM="15.10.2025" 
             BESCHREIBUNG="Spaghetti Bolognese" 
             PREIS_STUDENT="4,00"/>
        <ROW MENSA="Mensa Garbsen" DATUM="15.10.2025" 
             BESCHREIBUNG="Spaghetti Bolognese" 
             PREIS_STUDENT="3,50"/>
    </ROWDATA>
</DATAPACKET>'''
    
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
        f.write(test_xml)
        temp_file = f.name
    
    try:
        mensa_data = parse_mensa_data(temp_file)
        
        # Should have the meal at all 3 mensas
        assert "Hauptmensa" in mensa_data, "Hauptmensa should be in the data"
        assert "Contine" in mensa_data, "Contine should be in the data"
        assert "Mensa Garbsen" in mensa_data, "Mensa Garbsen should be in the data"
        
        assert len(mensa_data["Hauptmensa"]["15.10.2025"]) == 1, "Should have 1 meal at Hauptmensa"
        assert len(mensa_data["Contine"]["15.10.2025"]) == 1, "Should have 1 meal at Contine"
        assert len(mensa_data["Mensa Garbsen"]["15.10.2025"]) == 1, "Should have 1 meal at Mensa Garbsen"
        
        print("✓ Test passed! Same meal at different mensas is correctly kept.")
        return True
        
    finally:
        os.unlink(temp_file)


def test_complex_duplicate_scenario():
    """Test a complex scenario with various types of duplicates"""
    
    print("\nTesting complex duplicate scenario...")
    
    test_xml = '''<?xml version="1.0" encoding="utf-8"?>
<DATAPACKET>
    <ROWDATA>
        <ROW MENSA="Hauptmensa" DATUM="15.10.2025" 
             BESCHREIBUNG="Meal A" 
             PREIS_STUDENT="3,50"/>
        <ROW MENSA="Hauptmensa" DATUM="15.10.2025" 
             BESCHREIBUNG="Meal B" 
             PREIS_STUDENT="4,00"/>
        <ROW MENSA="Hauptmensa" DATUM="15.10.2025" 
             BESCHREIBUNG="Meal A" 
             PREIS_STUDENT="3,50"/>
        <ROW MENSA="Hauptmensa" DATUM="16.10.2025" 
             BESCHREIBUNG="Meal A" 
             PREIS_STUDENT="3,50"/>
        <ROW MENSA="Contine" DATUM="15.10.2025" 
             BESCHREIBUNG="Meal A" 
             PREIS_STUDENT="4,50"/>
        <ROW MENSA="Hauptmensa" DATUM="15.10.2025" 
             BESCHREIBUNG="Meal C" 
             PREIS_STUDENT="5,00"/>
        <ROW MENSA="Hauptmensa" DATUM="15.10.2025" 
             BESCHREIBUNG="Meal B" 
             PREIS_STUDENT="4,00"/>
    </ROWDATA>
</DATAPACKET>'''
    
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
        f.write(test_xml)
        temp_file = f.name
    
    try:
        mensa_data = parse_mensa_data(temp_file)
        
        # Check Hauptmensa on 15.10.2025: should have Meal A, B, C (3 unique meals)
        hauptmensa_oct15 = mensa_data["Hauptmensa"]["15.10.2025"]
        print(f"Hauptmensa 15.10.2025: {len(hauptmensa_oct15)} meals")
        assert len(hauptmensa_oct15) == 3, f"Expected 3 unique meals, got {len(hauptmensa_oct15)}"
        
        descriptions = [meal['description'] for meal in hauptmensa_oct15]
        assert "Meal A" in descriptions
        assert "Meal B" in descriptions
        assert "Meal C" in descriptions
        
        # Check Hauptmensa on 16.10.2025: should have Meal A
        hauptmensa_oct16 = mensa_data["Hauptmensa"]["16.10.2025"]
        print(f"Hauptmensa 16.10.2025: {len(hauptmensa_oct16)} meals")
        assert len(hauptmensa_oct16) == 1, f"Expected 1 meal, got {len(hauptmensa_oct16)}"
        assert hauptmensa_oct16[0]['description'] == "Meal A"
        
        # Check Contine on 15.10.2025: should have Meal A
        contine_oct15 = mensa_data["Contine"]["15.10.2025"]
        print(f"Contine 15.10.2025: {len(contine_oct15)} meals")
        assert len(contine_oct15) == 1, f"Expected 1 meal, got {len(contine_oct15)}"
        assert contine_oct15[0]['description'] == "Meal A"
        
        print("✓ Test passed! Complex duplicate scenario handled correctly.")
        return True
        
    finally:
        os.unlink(temp_file)


if __name__ == "__main__":
    try:
        success = True
        success = test_duplicate_meals_same_date() and success
        success = test_duplicates_different_dates() and success
        success = test_duplicates_different_mensas() and success
        success = test_complex_duplicate_scenario() and success
        
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
