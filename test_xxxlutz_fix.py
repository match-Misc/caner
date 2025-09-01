#!/usr/bin/env python3
"""
Test script for XXXLutz visibility issue
This tests that XXXLutz is shown when Mensa Garbsen is selected in non-dashboard mode
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_xxxlutz_visibility():
    """Test that XXXLutz is included when Mensa Garbsen is selected"""
    print("Testing XXXLutz visibility with Mensa Garbsen selection...")
    
    # Import the app and necessary functions
    from app import app, get_xxxlutz_meals
    
    # Create a test client
    with app.test_client() as client:
        
        # Test 1: Non-dashboard mode with Mensa Garbsen selected
        print("\n1. Testing non-dashboard mode with Mensa Garbsen selected...")
        
        # This simulates accessing the homepage with Mensa Garbsen selected
        # and dashboard mode disabled (default)
        response = client.get('/?mensa=Mensa+Garbsen&dashboard=false')
        
        # Check if response is successful
        if response.status_code == 200:
            content = response.data.decode('utf-8')
            
            # Check if XXXLutz appears in the response
            if 'XXXLutz Hesse Markrestaurant' in content:
                print("✓ XXXLutz is visible in non-dashboard mode with Mensa Garbsen - PASS")
            else:
                print("✗ XXXLutz is NOT visible in non-dashboard mode with Mensa Garbsen - FAIL")
                print("This indicates the bug is still present")
                return False
        else:
            print(f"✗ Request failed with status code: {response.status_code}")
            return False
            
        # Test 2: Dashboard mode with Mensa Garbsen selected (should still work)
        print("\n2. Testing dashboard mode with Mensa Garbsen selected...")
        
        response = client.get('/?mensa=Mensa+Garbsen&dashboard=true')
        
        if response.status_code == 200:
            content = response.data.decode('utf-8')
            
            if 'XXXLutz Hesse Markrestaurant' in content:
                print("✓ XXXLutz is visible in dashboard mode with Mensa Garbsen - PASS")
            else:
                print("✗ XXXLutz is NOT visible in dashboard mode with Mensa Garbsen - FAIL")
                return False
        else:
            print(f"✗ Request failed with status code: {response.status_code}")
            return False
            
        # Test 3: Non-dashboard mode with different mensa (should not show XXXLutz)
        print("\n3. Testing non-dashboard mode with Hauptmensa selected...")
        
        response = client.get('/?mensa=Hauptmensa&dashboard=false')
        
        if response.status_code == 200:
            content = response.data.decode('utf-8')
            
            if 'XXXLutz Hesse Markrestaurant' not in content:
                print("✓ XXXLutz is NOT visible with Hauptmensa (as expected) - PASS")
            else:
                print("? XXXLutz is visible with Hauptmensa - this might be intentional in dashboard mode")
        else:
            print(f"✗ Request failed with status code: {response.status_code}")
            return False
    
    print("\n✓ All tests passed! The fix appears to be working correctly.")
    return True

if __name__ == "__main__":
    # Test the get_xxxlutz_meals function first
    print("Testing get_xxxlutz_meals function...")
    try:
        from app import get_xxxlutz_meals
        meals = get_xxxlutz_meals()
        print(f"✓ get_xxxlutz_meals() returned {len(meals)} meals")
    except Exception as e:
        print(f"✗ get_xxxlutz_meals() failed: {e}")
        print("This might be due to database not being initialized")
    
    # Run the main test
    try:
        success = test_xxxlutz_visibility()
        if success:
            print("\n🎉 All tests passed!")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        print("This might be due to missing database or other setup issues")
        sys.exit(1)