import json
import unittest

import studifutter


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        return FakeResponse(self.responses.pop(0))


class StudiFutterTest(unittest.TestCase):
    def setUp(self):
        studifutter._canteen_cache["loaded_at"] = 0
        studifutter._canteen_cache["items"] = []

    def test_parse_caner_date(self):
        self.assertEqual(studifutter.parse_caner_date("04.06.2026"), "2026-06-04")

    def test_normalize_meal_name_collapses_spacing_and_case(self):
        self.assertEqual(
            studifutter.normalize_meal_name("  Frisches  Putenschnitzel , Pommes "),
            "frisches putenschnitzel, pommes",
        )

    def test_resolve_studifutter_canteen_id_uses_alias_or_external_identifier(self):
        session = FakeSession(
            [
                {
                    "data": [
                        {
                            "id": "canteen-1",
                            "alias": "Mensa Garbsen",
                            "external_identifier": "PZH",
                        }
                    ]
                }
            ]
        )

        self.assertEqual(
            studifutter.resolve_studifutter_canteen_id("Mensa Garbsen", session=session),
            "canteen-1",
        )

    def test_find_matching_foodoffer_matches_de_translation_exactly(self):
        offers = [
            {
                "alias": "Different",
                "food": {
                    "alias": "Also different",
                    "translations": [
                        {
                            "languages_code": "de-DE",
                            "name": "Hausgemachte Pasta, alla Norma",
                        }
                    ],
                },
            }
        ]

        self.assertIs(
            studifutter.find_matching_foodoffer(
                offers,
                "Hausgemachte Pasta, alla Norma",
            ),
            offers[0],
        )

    def test_find_matching_foodoffer_does_not_fuzzy_match(self):
        offers = [
            {
                "alias": "Frisches Putenschnitzel, Chili-Hollandaise, Pommes frites",
                "food": {"alias": "Frisches Putenschnitzel"},
            }
        ]

        self.assertIsNone(
            studifutter.find_matching_foodoffer(
                offers,
                "Putenschnitzel mit Pommes",
            )
        )

    def test_find_meal_image_returns_proxied_directus_asset_url(self):
        image_id = "4ff2b6bf-1239-4a2b-ade2-73196977b777"
        session = FakeSession(
            [
                {
                    "data": [
                        {
                            "id": "canteen-1",
                            "alias": "Mensa Garbsen",
                            "external_identifier": "Mensa Garbsen",
                        }
                    ]
                },
                {
                    "data": [
                        {
                            "alias": "Frisches Putenschnitzel, Chili-Hollandaise, Pommes frites",
                            "food": {
                                "alias": "Frisches Putenschnitzel, Chili-Hollandaise, Pommes frites",
                                "image": image_id,
                                "image_remote_url": None,
                                "translations": [],
                            },
                        }
                    ]
                },
            ]
        )

        result = studifutter.find_meal_image(
            "Frisches Putenschnitzel, Chili-Hollandaise, Pommes frites",
            "Mensa Garbsen",
            "04.06.2026",
            session=session,
        )

        self.assertEqual(result["image_url"], f"/api/studifutter/assets/{image_id}")
        foodoffer_params = session.calls[1]["params"]
        self.assertEqual(foodoffer_params["limit"], "-1")
        self.assertEqual(
            json.loads(foodoffer_params["filter"])["_and"][0]["canteen"]["_eq"],
            "canteen-1",
        )


if __name__ == "__main__":
    unittest.main()
