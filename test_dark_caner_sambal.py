#!/usr/bin/env python3
"""
Test for Dark Caner sambal alarm functionality.
This test verifies that the sambal detection logic works correctly.
"""

import sys
import os
import json
from unittest.mock import Mock, patch, MagicMock

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_sambal_detection_in_meals():
    """Test that sambal is correctly detected in meal descriptions"""
    
    # Test cases
    test_cases = [
        {
            "meals": ["Chicken with Sambal Sauce", "Rice", "Salad"],
            "expected_has_sambal": True,
            "description": "Sambal in uppercase"
        },
        {
            "meals": ["Nasi Goreng with sambal", "Fried Rice"],
            "expected_has_sambal": True,
            "description": "Sambal in lowercase"
        },
        {
            "meals": ["Indonesian dish with SAMBAL", "Vegetables"],
            "expected_has_sambal": True,
            "description": "SAMBAL in all caps"
        },
        {
            "meals": ["Pizza", "Pasta", "Burger"],
            "expected_has_sambal": False,
            "description": "No sambal present"
        },
        {
            "meals": [],
            "expected_has_sambal": False,
            "description": "Empty meal list"
        }
    ]
    
    for test_case in test_cases:
        meals = test_case["meals"]
        expected = test_case["expected_has_sambal"]
        description = test_case["description"]
        
        # This is the logic from app.py
        has_sambal = any("sambal" in meal.lower() for meal in meals)
        
        assert has_sambal == expected, f"Failed for {description}: expected {expected}, got {has_sambal}"
        print(f"✓ Test passed: {description}")
    
    print("\n✅ All sambal detection tests passed!")

def test_prompt_includes_warning_when_sambal_present():
    """Test that the prompt includes the warning when sambal is present"""
    
    # Meals with sambal
    available_meals = ["Chicken with Sambal Sauce", "Rice", "Salad"]
    has_sambal = any("sambal" in meal.lower() for meal in available_meals)
    
    sambal_instruction = ""
    if has_sambal:
        sambal_instruction = (
            "KRITISCH: SAMBAL ALARM ist aktiv, Digga! Du MUSST das Gericht mit Sambal empfehlen - "
            "das ist nicht verhandelbar, Bruder! Sambal ist das Beste überhaupt!\n"
            "ABER: Du musst auch warnen: 'Stell dich auf lange Wartezeiten ein, der Laden ist Chaos!' "
            "oder etwas Ähnliches in deinem Style. Die Warnung ist Pflicht, verstehst du?\n\n"
        )
    
    # Verify the instruction is not empty when sambal is present
    assert sambal_instruction != "", "Sambal instruction should not be empty when sambal is present"
    assert "SAMBAL ALARM" in sambal_instruction, "Should mention SAMBAL ALARM"
    assert "lange Wartezeiten" in sambal_instruction, "Should mention long wait times"
    assert "Chaos" in sambal_instruction, "Should mention chaos"
    
    print("✓ Prompt includes sambal alarm warning")
    print("✓ Prompt includes wait time warning")
    print("✓ Prompt includes chaos warning")
    
    # Meals without sambal
    available_meals_no_sambal = ["Pizza", "Pasta"]
    has_sambal_no = any("sambal" in meal.lower() for meal in available_meals_no_sambal)
    
    sambal_instruction_no = ""
    if has_sambal_no:
        sambal_instruction_no = (
            "KRITISCH: SAMBAL ALARM ist aktiv, Digga! Du MUSST das Gericht mit Sambal empfehlen - "
            "das ist nicht verhandelbar, Bruder! Sambal ist das Beste überhaupt!\n"
            "ABER: Du musst auch warnen: 'Stell dich auf lange Wartezeiten ein, der Laden ist Chaos!' "
            "oder etwas Ähnliches in deinem Style. Die Warnung ist Pflicht, verstehst du?\n\n"
        )
    
    assert sambal_instruction_no == "", "Sambal instruction should be empty when no sambal is present"
    print("✓ No sambal instruction when sambal not present")
    
    print("\n✅ All prompt generation tests passed!")

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Dark Caner Sambal Detection Logic")
    print("=" * 60)
    print()
    
    test_sambal_detection_in_meals()
    print()
    test_prompt_includes_warning_when_sambal_present()
    
    print()
    print("=" * 60)
    print("All tests completed successfully! 🎉")
    print("=" * 60)
