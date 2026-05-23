import unittest

from i18n import (
    DEFAULT_LANGUAGE,
    format_date_for_language,
    get_meal_display_name,
    resolve_language,
    translate_nutrient_label,
    translate_nutrient_value,
)


class DummyArgs:
    def __init__(self, values):
        self.values = values

    def get(self, key):
        return self.values.get(key)


class DummyRequest:
    def __init__(self, args=None, cookies=None):
        self.args = DummyArgs(args or {})
        self.cookies = cookies or {}


class DummyMeal:
    def __init__(self, description, description_en=None):
        self.description = description
        self.description_en = description_en


class I18nTest(unittest.TestCase):
    def test_resolve_language_query_over_cookie(self):
        request = DummyRequest(args={"lang": "en"}, cookies={"language": "de"})
        self.assertEqual(resolve_language(request), "en")

    def test_resolve_language_defaults_for_unknown_language(self):
        request = DummyRequest(args={"lang": "fr"})
        self.assertEqual(resolve_language(request), DEFAULT_LANGUAGE)

    def test_meal_display_uses_english_with_german_fallback(self):
        self.assertEqual(
            get_meal_display_name(DummyMeal("Kartoffelsuppe", "Potato soup"), "en"),
            "Potato soup",
        )
        self.assertEqual(
            get_meal_display_name(DummyMeal("Kartoffelsuppe"), "en"),
            "Kartoffelsuppe",
        )

    def test_format_date_for_language(self):
        self.assertEqual(format_date_for_language("20.05.2024", "de"), "20.05.2024, Montag")
        self.assertEqual(format_date_for_language("20.05.2024", "en"), "20.05.2024, Monday")

    def test_nutrient_translation(self):
        self.assertEqual(translate_nutrient_label("Eiweiß", "en"), "Protein")
        self.assertEqual(
            translate_nutrient_value("10g, davon Zucker 2g", "en"),
            "10g, of which sugars 2g",
        )


if __name__ == "__main__":
    unittest.main()
