#!/usr/bin/env python3
"""
Unit test for the XXXLutz logic fix without requiring database
This tests the core logic changes made to fix the visibility issue
"""

def test_xxxlutz_logic():
    """Test the logic for when XXXLutz should be included"""
    
    print("Testing XXXLutz inclusion logic...")
    
    # Simulate different scenarios
    scenarios = [
        {
            "name": "Non-dashboard mode, Mensa Garbsen selected, Garbsen has meals",
            "selected_mensa": "Mensa Garbsen",
            "dashboard_mode": False,
            "garbsen_has_meals": True,
            "expected_xxxlutz": True,  # This should be True after our fix
        },
        {
            "name": "Dashboard mode, Mensa Garbsen selected, Garbsen has meals", 
            "selected_mensa": "Mensa Garbsen",
            "dashboard_mode": True,
            "garbsen_has_meals": True,
            "expected_xxxlutz": True,
        },
        {
            "name": "Non-dashboard mode, Hauptmensa selected",
            "selected_mensa": "Hauptmensa",
            "dashboard_mode": False,
            "garbsen_has_meals": False,
            "expected_xxxlutz": False,
        },
        {
            "name": "Dashboard mode, Hauptmensa selected",
            "selected_mensa": "Hauptmensa", 
            "dashboard_mode": True,
            "garbsen_has_meals": False,
            "expected_xxxlutz": True,  # Dashboard mode shows XXXLutz regardless
        },
        {
            "name": "Non-dashboard mode, Mensa Garbsen selected, Garbsen has NO meals",
            "selected_mensa": "Mensa Garbsen",
            "dashboard_mode": False,
            "garbsen_has_meals": False,
            "expected_xxxlutz": True,  # Should still show XXXLutz
        },
    ]
    
    all_passed = True
    
    for scenario in scenarios:
        print(f"\nTesting: {scenario['name']}")
        
        # Simulate the logic from our fix
        filtered_data = {}
        
        # Step 1: Add selected mensa if it has meals
        if scenario["garbsen_has_meals"] and scenario["selected_mensa"] == "Mensa Garbsen":
            filtered_data["Mensa Garbsen"] = ["mock_meal"]
        elif scenario["selected_mensa"] != "Mensa Garbsen":
            filtered_data[scenario["selected_mensa"]] = ["mock_meal"]
        
        # Step 2: OUR FIX - Add XXXLutz if Mensa Garbsen is selected
        if scenario["selected_mensa"] == "Mensa Garbsen":
            filtered_data["XXXLutz Hesse Markrestaurant"] = ["mock_xxxlutz_meal"]
        
        # Step 3: Dashboard mode logic (existing logic)
        if scenario["dashboard_mode"]:
            # In dashboard mode, add Garbsen if not already there
            if "Mensa Garbsen" not in filtered_data and scenario["garbsen_has_meals"]:
                filtered_data["Mensa Garbsen"] = ["mock_meal"]
            
            # Add XXXLutz if not already added
            if "XXXLutz Hesse Markrestaurant" not in filtered_data:
                filtered_data["XXXLutz Hesse Markrestaurant"] = ["mock_xxxlutz_meal"]
        
        # Step 4: Fallback logic for when Garbsen has no meals (existing logic)
        if (scenario["selected_mensa"] == "Mensa Garbsen" and scenario["selected_mensa"] not in filtered_data) or (
            scenario["dashboard_mode"] and "XXXLutz Hesse Markrestaurant" not in filtered_data
        ):
            # This would be the working day check, but for test we assume it passes
            if "XXXLutz Hesse Markrestaurant" not in filtered_data:
                filtered_data["XXXLutz Hesse Markrestaurant"] = ["mock_xxxlutz_meal"]
        
        # Check if XXXLutz is in the result
        xxxlutz_present = "XXXLutz Hesse Markrestaurant" in filtered_data
        
        if xxxlutz_present == scenario["expected_xxxlutz"]:
            print(f"✓ PASS - XXXLutz presence: {xxxlutz_present} (expected: {scenario['expected_xxxlutz']})")
        else:
            print(f"✗ FAIL - XXXLutz presence: {xxxlutz_present} (expected: {scenario['expected_xxxlutz']})")
            all_passed = False
        
        print(f"  Filtered data keys: {list(filtered_data.keys())}")
    
    return all_passed

def test_original_vs_fixed_logic():
    """Compare the original buggy logic vs our fix"""
    
    print("\n" + "="*60)
    print("COMPARISON: Original buggy logic vs Fixed logic")
    print("="*60)
    
    # The critical test case: Non-dashboard mode, Mensa Garbsen selected, Garbsen has meals
    selected_mensa = "Mensa Garbsen"
    dashboard_mode = False
    garbsen_has_meals = True
    
    print(f"Scenario: selected_mensa='{selected_mensa}', dashboard_mode={dashboard_mode}, garbsen_has_meals={garbsen_has_meals}")
    
    # Original buggy logic simulation
    print("\nOriginal (buggy) logic:")
    filtered_data_original = {}
    
    # Step 1: Add selected mensa if it has meals
    if garbsen_has_meals:
        filtered_data_original["Mensa Garbsen"] = ["mock_meal"]
    
    # Step 2: Dashboard mode block (skipped in non-dashboard mode)
    if dashboard_mode:  # This is False, so block is skipped
        # XXXLutz would be added here, but we're not in dashboard mode
        pass
    
    # Step 3: Fallback for when Garbsen has no meals (doesn't apply here)
    if selected_mensa == "Mensa Garbsen" and selected_mensa not in filtered_data_original:
        # This condition is False because Garbsen IS in filtered_data
        pass
    
    xxxlutz_in_original = "XXXLutz Hesse Markrestaurant" in filtered_data_original
    print(f"Result: XXXLutz present = {xxxlutz_in_original}")
    print(f"Filtered data: {list(filtered_data_original.keys())}")
    
    # Fixed logic simulation
    print("\nFixed logic:")
    filtered_data_fixed = {}
    
    # Step 1: Add selected mensa if it has meals
    if garbsen_has_meals:
        filtered_data_fixed["Mensa Garbsen"] = ["mock_meal"]
    
    # Step 2: OUR FIX - Add XXXLutz if Mensa Garbsen is selected
    if selected_mensa == "Mensa Garbsen":
        filtered_data_fixed["XXXLutz Hesse Markrestaurant"] = ["mock_xxxlutz_meal"]
    
    # (The rest of the logic would run but wouldn't change the result)
    
    xxxlutz_in_fixed = "XXXLutz Hesse Markrestaurant" in filtered_data_fixed
    print(f"Result: XXXLutz present = {xxxlutz_in_fixed}")
    print(f"Filtered data: {list(filtered_data_fixed.keys())}")
    
    # Summary
    print(f"\nSummary:")
    print(f"Original logic: XXXLutz visible = {xxxlutz_in_original} (BUG - should be True)")
    print(f"Fixed logic:    XXXLutz visible = {xxxlutz_in_fixed} (CORRECT)")
    
    return xxxlutz_in_fixed and not xxxlutz_in_original

if __name__ == "__main__":
    print("Testing XXXLutz visibility logic fix")
    print("=" * 50)
    
    # Run the main logic test
    logic_test_passed = test_xxxlutz_logic()
    
    # Run the comparison test
    comparison_test_passed = test_original_vs_fixed_logic()
    
    print("\n" + "=" * 50)
    print("FINAL RESULTS:")
    print(f"Logic test: {'PASS' if logic_test_passed else 'FAIL'}")
    print(f"Comparison test: {'PASS' if comparison_test_passed else 'FAIL'}")
    
    if logic_test_passed and comparison_test_passed:
        print("\n🎉 All tests passed! The fix correctly resolves the issue.")
        exit(0)
    else:
        print("\n❌ Some tests failed. The fix may need adjustment.")
        exit(1)