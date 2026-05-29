import unittest

from comment_translation import parse_comment_translation_response
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

    def test_parse_comment_translation_response(self):
        result = parse_comment_translation_response(
            '{"de": "Sehr gut", "en": "Very good"}'
        )
        self.assertEqual(result, {"de": "Sehr gut", "en": "Very good"})

    def test_parse_comment_translation_response_accepts_code_fence(self):
        result = parse_comment_translation_response(
            '```json\n{"de": "Schlecht", "en": "Bad"}\n```'
        )
        self.assertEqual(result, {"de": "Schlecht", "en": "Bad"})


if __name__ == "__main__":
    unittest.main()
