#!/usr/bin/env python3
"""
Test script for RKR penalty system
"""

# Test the penalty keywords and calculation logic
PENALTY_KEYWORDS = [
    # Vegetables
    "gemüse",
    "zucchini",
    "paprika",
    "karotten",
    "brokkoli",
    "blumenkohl",
    "spinat",
    "aubergine",
    "erbsen",
    "bohnen",
    "spargel",
    "lauch",
    "sellerie",
    "zwiebeln",
    "knoblauch",
    "schalotten",
    "salat",
    "rucola",
    "feldsalat",
    "eisbergsalat",
    # Mushrooms
    "champignons",
    "pfifferlinge",
    "steinpilze",
    "pilze",
    # Fruits
    "äpfel",
    "birnen",
    "quitten",
    "kirschen",
    "pflaumen",
    "aprikosen",
    "pfirsiche",
    "nektarinen",
    "erdbeeren",
    "himbeeren",
    "heidelbeeren",
    "brombeeren",
    "johannisbeeren",
    "orangen",
    "mandarinen",
    "zitronen",
    "limetten",
    "grapefruits",
    "bananen",
    "ananas",
    "mango",
    "kiwi",
    "melonen",
    "rosinen",
    "getrocknete pflaumen",
    "datteln",
    # Fish & Seafood
    "lachs",
    "thunfisch",
    "forelle",
    "kabeljau",
    "hering",
    "garnelen",
    "krabben",
    "muscheln",
    "austern",
    "tintenfisch",
    "hummer",
    # Hidden Vegetables/Fruits
    "gemüseaufläufe",
    "gratins mit gemüse",
    "pizza mit gemüse oder pilzen",
    "wraps mit salat",
    "sandwiches mit gemüse",
    "burger mit tomaten oder gurken",
    "soßen mit gemüsebasis",
    "tomatensoße",
    "ratatouille",
    "gemüsesuppe",
    "desserts mit obst",
    "apfelkuchen",
    "erdbeertorte",
    "obstsalat",
    # Plant-based Components
    "viel petersilie",
    "basilikum",
    "koriander",
    "dill",
    "soja-fleischalternativen",
    "gemüse-fleischalternativen",
    "gemüsesäfte",
    "smoothies",
    "karottensaft",
    "multivitaminsaft",
]


def calculate_rkr_real(protein_g, price_student, meal_description):
    """Test version of RKR calculation"""
    rkr_value = protein_g / price_student if price_student > 0 else 0

    if rkr_value == 0.0:
        return 0.0

    description_lower = meal_description.lower() if meal_description else ""

    # Special handling for "erbsen" - multiply by -1
    if "erbsen" in description_lower:
        rkr_value *= -1
        print(f"  -> Erbsen detected! Multiplied by -1: {rkr_value}")

    # Apply regular penalties for other keywords (excluding "erbsen")
    penalty_applied = False
    for keyword in PENALTY_KEYWORDS:
        if keyword != "erbsen" and keyword in description_lower:
            rkr_value /= 2
            print(f"  -> Penalty applied for '{keyword}': divided by 2 = {rkr_value}")
            penalty_applied = True

    if not penalty_applied and "erbsen" not in description_lower:
        print("  -> No penalties applied")

    return round(rkr_value, 2)


# Test cases
test_cases = [
    # Basic test - no penalties
    {
        "description": "Schnitzel mit Pommes",
        "protein": 25.0,
        "price": 5.0,
        "expected": 5.0,
    },
    # Single penalty - regular vegetable
    {
        "description": "Schnitzel mit Paprika",
        "protein": 25.0,
        "price": 5.0,
        "expected": 2.5,
    },
    # Erbsen test - should become negative
    {"description": "Erbseneintopf", "protein": 10.0, "price": 4.0, "expected": -2.5},
    # Multiple penalties
    {
        "description": "Gemüsepfanne mit Paprika und Zwiebeln",
        "protein": 8.0,
        "price": 4.0,
        "expected": 0.25,
    },
    # Erbsen with other penalties
    {
        "description": "Erbsen mit Paprika",
        "protein": 12.0,
        "price": 3.0,
        "expected": -2.0,
    },
    # Hidden vegetable
    {
        "description": "Pizza mit Gemüse",
        "protein": 15.0,
        "price": 6.0,
        "expected": 1.25,
    },
    # Fruit test
    {
        "description": "Dessert mit Äpfeln",
        "protein": 5.0,
        "price": 3.0,
        "expected": 0.83,
    },
    # Fish test
    {"description": "Lachs mit Reis", "protein": 20.0, "price": 8.0, "expected": 1.25},
]

print("Testing RKR Penalty System")
print("=" * 50)

for i, test in enumerate(test_cases, 1):
    print(f"\nTest {i}: {test['description']}")
    print(f"Protein: {test['protein']}g, Price: {test['price']}€")

    result = calculate_rkr_real(test["protein"], test["price"], test["description"])
    print(f"Result: {result} RkrR")

    # Check if result matches expected (with small tolerance for floating point)
    if abs(result - test["expected"]) < 0.01:
        print("✅ PASS")
    else:
        print(f"❌ FAIL - Expected: {test['expected']}")

print("\n" + "=" * 50)
print("RKR Testing Complete!")

# Test keyword matching
print("\nTesting keyword detection:")
test_keywords = ["erbsen", "paprika", "lachs", "gemüse", "zwiebeln", "bananen"]
for keyword in test_keywords:
    found = keyword in PENALTY_KEYWORDS
    print(f"'{keyword}' in penalty list: {found}")
