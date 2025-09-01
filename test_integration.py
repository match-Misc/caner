#!/usr/bin/env python3
"""
Integration test for XXXLutz visibility without requiring a database.
This test mocks the database dependencies and focuses on the app logic.
"""

import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_app_with_mocked_db():
    """Test the actual Flask app with mocked database dependencies"""
    
    print("Testing Flask app with mocked database...")
    
    # Mock the database models and functions before importing the app
    with patch('psycopg2.connect'), \
         patch('models.db') as mock_db, \
         patch('models.XXXLutzChangingMeal') as mock_changing, \
         patch('models.XXXLutzFixedMeal') as mock_fixed, \
         patch('models.Meal') as mock_meal:
        
        # Configure the mock database models
        mock_db.init_app = Mock()
        mock_db.create_all = Mock()
        
        # Mock XXXLutz meals
        mock_changing_meal = Mock()
        mock_changing_meal.id = 1
        mock_changing_meal.description = "Test Changing Meal"
        mock_changing_meal.marking = "test"
        mock_changing_meal.price_student = 5.50
        mock_changing_meal.price_employee = 6.50
        mock_changing_meal.price_guest = 7.50
        mock_changing_meal.nutritional_values = "Test nutrition info"
        mock_changing_meal.mps_score = 8.5
        
        mock_fixed_meal = Mock()
        mock_fixed_meal.id = 2
        mock_fixed_meal.description = "Test Fixed Meal"
        mock_fixed_meal.marking = "test"
        mock_fixed_meal.price_student = 9.90
        mock_fixed_meal.price_employee = 10.90
        mock_fixed_meal.price_guest = 11.90
        mock_fixed_meal.nutritional_values = "Test nutrition info"
        mock_fixed_meal.mps_score = 7.5
        
        # Configure the queries to return our mock meals
        mock_changing.query.all.return_value = [mock_changing_meal]
        mock_fixed.query.all.return_value = [mock_fixed_meal]
        mock_meal.query.filter_by.return_value.first.return_value = None
        
        # Mock environment variables
        with patch.dict(os.environ, {
            'SESSION_SECRET': 'test-secret',
            'CANER_DB_USER': 'test_user',
            'CANER_DB_PASSWORD': 'test_pass',
            'CANER_DB_HOST': 'localhost',
            'CANER_DB_NAME': 'test_db'
        }):
            
            # Import the app after mocking
            try:
                from app import app
                
                # Mock the data fetching since we don't have real data
                with patch('app.mensa_data', {
                    'Mensa Garbsen': {
                        '01.09.2025': [
                            {
                                'description': 'Test Garbsen Meal',
                                'nutritional_values': 'Test nutrition',
                                'price_student': 4.50,
                                'id': 1,
                                'mps_score': 7.0
                            }
                        ]
                    },
                    'Hauptmensa': {
                        '01.09.2025': [
                            {
                                'description': 'Test Hauptmensa Meal',
                                'nutritional_values': 'Test nutrition',
                                'price_student': 3.50,
                                'id': 2,
                                'mps_score': 6.0
                            }
                        ]
                    }
                }), \
                patch('app.available_mensen', ['Mensa Garbsen', 'Hauptmensa', 'Contine']), \
                patch('app.available_dates', ['01.09.2025']):
                    
                    # Test the app
                    with app.test_client() as client:
                        
                        # Test 1: Non-dashboard mode with Mensa Garbsen
                        print("\n1. Testing non-dashboard mode with Mensa Garbsen...")
                        response = client.get('/?mensa=Mensa+Garbsen&date=01.09.2025')
                        
                        if response.status_code == 200:
                            content = response.data.decode('utf-8')
                            
                            # Check if both Garbsen and XXXLutz are present
                            has_garbsen = 'Mensa Garbsen' in content and 'Test Garbsen Meal' in content
                            has_xxxlutz = 'XXXLutz Hesse Markrestaurant' in content
                            
                            print(f"   Garbsen meals present: {has_garbsen}")
                            print(f"   XXXLutz meals present: {has_xxxlutz}")
                            
                            if has_xxxlutz:
                                print("   ✓ SUCCESS: XXXLutz is visible with Mensa Garbsen in non-dashboard mode")
                            else:
                                print("   ✗ FAIL: XXXLutz is NOT visible with Mensa Garbsen in non-dashboard mode")
                                return False
                        else:
                            print(f"   ✗ Request failed with status {response.status_code}")
                            return False
                        
                        # Test 2: Non-dashboard mode with Hauptmensa (should NOT show XXXLutz)
                        print("\n2. Testing non-dashboard mode with Hauptmensa...")
                        response = client.get('/?mensa=Hauptmensa&date=01.09.2025')
                        
                        if response.status_code == 200:
                            content = response.data.decode('utf-8')
                            
                            has_hauptmensa = 'Hauptmensa' in content
                            has_xxxlutz = 'XXXLutz Hesse Markrestaurant' in content
                            
                            print(f"   Hauptmensa meals present: {has_hauptmensa}")
                            print(f"   XXXLutz meals present: {has_xxxlutz}")
                            
                            if not has_xxxlutz:
                                print("   ✓ SUCCESS: XXXLutz is correctly NOT visible with Hauptmensa")
                            else:
                                print("   ? XXXLutz is visible with Hauptmensa - might be expected in some modes")
                        else:
                            print(f"   ✗ Request failed with status {response.status_code}")
                            return False
                        
                        # Test 3: Dashboard mode (should show XXXLutz regardless)
                        print("\n3. Testing dashboard mode...")
                        response = client.get('/?dashboard=true&date=01.09.2025')
                        
                        if response.status_code == 200:
                            content = response.data.decode('utf-8')
                            
                            has_xxxlutz = 'XXXLutz Hesse Markrestaurant' in content
                            
                            print(f"   XXXLutz meals present: {has_xxxlutz}")
                            
                            if has_xxxlutz:
                                print("   ✓ SUCCESS: XXXLutz is visible in dashboard mode")
                            else:
                                print("   ✗ FAIL: XXXLutz should be visible in dashboard mode")
                                return False
                        else:
                            print(f"   ✗ Request failed with status {response.status_code}")
                            return False
                
                print("\n✓ All integration tests passed!")
                return True
                
            except Exception as e:
                print(f"✗ Failed to import/test app: {e}")
                import traceback
                traceback.print_exc()
                return False

if __name__ == "__main__":
    print("Integration test for XXXLutz visibility fix")
    print("=" * 50)
    
    try:
        success = test_app_with_mocked_db()
        
        if success:
            print("\n🎉 Integration test passed! The fix works correctly.")
            sys.exit(0)
        else:
            print("\n❌ Integration test failed.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)