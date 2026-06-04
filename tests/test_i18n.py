import os
import unittest
from unittest.mock import patch

from flask import Flask

from i18n import (
    DEFAULT_LANGUAGE,
    format_date_for_language,
    get_marking_info,
    get_meal_display_name,
    get_recommendation_prompt,
    get_translations,
    resolve_language,
    set_language_cookie,
    translate_nutrient_label,
    translate_nutrient_value,
)


class DummyArgs:
    def __init__(self, values):
        self.values = values

    def get(self, key):
        return self.values.get(key)


class DummyAcceptLanguages:
    def __init__(self, match=None):
        self.match = match

    def best_match(self, supported, default=None):
        if self.match in supported:
            return self.match
        return default


class DummyRequest:
    def __init__(self, args=None, cookies=None, browser_language=None):
        self.args = DummyArgs(args or {})
        self.cookies = cookies or {}
        self.accept_languages = DummyAcceptLanguages(browser_language)


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

    def test_resolve_language_uses_browser_preference_without_cookie(self):
        request = DummyRequest(browser_language="en")
        self.assertEqual(resolve_language(request), "en")

    def test_resolve_language_cookie_over_browser_preference(self):
        request = DummyRequest(cookies={"language": "de"}, browser_language="en")
        self.assertEqual(resolve_language(request), "de")

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

    def test_marking_info_has_dark_variants(self):
        marking_info = get_marking_info("en")
        self.assertEqual(marking_info["f"]["dark_emoji"], "🦈")
        self.assertEqual(
            marking_info["q"]["dark_images"],
            [
                "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5f/Coat_of_arms_of_Saxony.svg/960px-Coat_of_arms_of_Saxony.svg.png"
            ],
        )

    def test_metadata_translations_exist_for_all_languages(self):
        for language in ("de", "en"):
            texts = get_translations(language)
            self.assertTrue(texts["meta_description"])
            self.assertTrue(texts["llms_summary"])
            self.assertTrue(texts["app_short_name"])

    def test_language_cookie_has_privacy_attributes(self):
        app = Flask(__name__)
        with app.test_request_context("/", base_url="https://example.test"):
            response = app.response_class("")
            set_language_cookie(response, "en")

        cookie = response.headers["Set-Cookie"]
        self.assertIn("language=en", cookie)
        self.assertIn("HttpOnly", cookie)
        self.assertIn("Secure", cookie)
        self.assertIn("SameSite=Lax", cookie)

    def test_persona_recommendation_prompt_language_selection(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIn(
                "in English", get_recommendation_prompt("en", "Marvin")
            )
            self.assertIn(
                "auf Deutsch", get_recommendation_prompt("de", "Marvin")
            )
            self.assertIn(
                "in English",
                get_recommendation_prompt("en", "Gordon Ramsay"),
            )
            self.assertIn(
                "auf Deutsch",
                get_recommendation_prompt("de", "Gordon Ramsay"),
            )
            self.assertIn(
                "in English",
                get_recommendation_prompt("en", "Rick Sanchez"),
            )
            self.assertIn(
                "auf Deutsch",
                get_recommendation_prompt("de", "Rick Sanchez"),
            )

    def test_removed_bob_persona_uses_generic_prompt(self):
        with patch.dict(os.environ, {}, clear=True):
            bob_prompt = get_recommendation_prompt("en", "Bob der Baumeister")
            generic_prompt = get_recommendation_prompt("en", "Ada Lovelace")

        self.assertEqual(bob_prompt, generic_prompt)
        self.assertNotIn("Bob the Builder", bob_prompt)

    def test_trump_recommendation_prompt_is_always_english(self):
        with patch.dict(os.environ, {}, clear=True):
            german_page_prompt = get_recommendation_prompt("de", "Donald Trump")
            english_page_prompt = get_recommendation_prompt("en", "Donald Trump")

        self.assertIn("in English", german_page_prompt)
        self.assertEqual(german_page_prompt, english_page_prompt)

    def test_persona_recommendation_prompt_env_override_wins(self):
        with patch.dict(
            os.environ,
            {"PROMPT_MARVIN_EN": "Override line one\\n{meal_list}"},
            clear=True,
        ):
            self.assertEqual(
                get_recommendation_prompt("en", "Marvin"),
                "Override line one\n{meal_list}",
            )

    def test_new_persona_recommendation_prompt_env_override_wins(self):
        with patch.dict(
            os.environ,
            {"PROMPT_RICK_EN": "Rick override\\n{meal_list}"},
            clear=True,
        ):
            self.assertEqual(
                get_recommendation_prompt("en", "Rick Sanchez"),
                "Rick override\n{meal_list}",
            )

    def test_custom_recommender_uses_generic_prompt_override(self):
        with patch.dict(
            os.environ,
            {"PROMPT_RECOMMENDATION_EN": "Generic English {recommender}"},
            clear=True,
        ):
            self.assertEqual(
                get_recommendation_prompt("en", "Ada Lovelace"),
                "Generic English {recommender}",
            )


if __name__ == "__main__":
    unittest.main()
