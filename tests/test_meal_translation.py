import unittest

from meal_translation import parse_translation_response


class MealTranslationTest(unittest.TestCase):
    def test_parse_translation_response_json_object(self):
        result = parse_translation_response(
            '{"Kartoffelsuppe": "Potato soup", "Nudeln": "Pasta"}',
            ["Kartoffelsuppe", "Nudeln"],
        )
        self.assertEqual(
            result,
            {"Kartoffelsuppe": "Potato soup", "Nudeln": "Pasta"},
        )

    def test_parse_translation_response_ignores_unknown_keys(self):
        result = parse_translation_response(
            '{"Kartoffelsuppe": "Potato soup", "Extra": "Ignore"}',
            ["Kartoffelsuppe"],
        )
        self.assertEqual(result, {"Kartoffelsuppe": "Potato soup"})

    def test_parse_translation_response_accepts_code_fence(self):
        result = parse_translation_response(
            '```json\n{"Kartoffelsuppe": "Potato soup"}\n```',
            ["Kartoffelsuppe"],
        )
        self.assertEqual(result, {"Kartoffelsuppe": "Potato soup"})


if __name__ == "__main__":
    unittest.main()
