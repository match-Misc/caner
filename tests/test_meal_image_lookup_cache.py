import unittest
from datetime import datetime, timedelta, timezone

from flask import Flask

from meal_image_lookup_cache import find_or_cache_meal_image
from models import Meal, MealImageLookupCache, db


IMAGE_ID = "4ff2b6bf-1239-4a2b-ade2-73196977b777"
RACED_IMAGE_ID = "f51a0a8a-3a13-44b3-95fb-4126b5d4a66f"


class FakeFinder:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, meal_description, mensa_name, selected_date):
        self.calls.append(
            {
                "meal_description": meal_description,
                "mensa_name": mensa_name,
                "selected_date": selected_date,
            }
        )
        return self.responses.pop(0)


class MealImageLookupCacheTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        self.app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        db.init_app(self.app)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()

        self.meal = Meal(description="Frisches Putenschnitzel")
        db.session.add(self.meal)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_positive_lookup_is_reused_indefinitely(self):
        now = datetime(2026, 6, 8, tzinfo=timezone.utc)
        finder = FakeFinder(
            [
                {
                    "image_file_id": IMAGE_ID,
                    "matched_name": "Frisches Putenschnitzel",
                }
            ]
        )

        first = find_or_cache_meal_image(
            self.meal,
            "Mensa Garbsen",
            "08.06.2026",
            21600,
            finder=finder,
            now=now,
        )
        second = find_or_cache_meal_image(
            self.meal,
            "Mensa Garbsen",
            "08.06.2026",
            21600,
            finder=finder,
            now=now + timedelta(days=365),
        )

        self.assertEqual(len(finder.calls), 1)
        self.assertEqual(first, second)
        self.assertEqual(first["image_url"], f"/api/studifutter/assets/{IMAGE_ID}")
        self.assertEqual(
            first["thumbnail_url"],
            f"/api/studifutter/assets/{IMAGE_ID}?variant=thumb",
        )

    def test_negative_lookup_cache_expires(self):
        now = datetime(2026, 6, 8, tzinfo=timezone.utc)
        finder = FakeFinder(
            [
                None,
                {
                    "image_file_id": IMAGE_ID,
                    "matched_name": "Frisches Putenschnitzel",
                },
            ]
        )

        first = find_or_cache_meal_image(
            self.meal,
            "Mensa Garbsen",
            "08.06.2026",
            21600,
            finder=finder,
            now=now,
        )
        fresh_negative = find_or_cache_meal_image(
            self.meal,
            "Mensa Garbsen",
            "08.06.2026",
            21600,
            finder=finder,
            now=now + timedelta(hours=1),
        )
        expired_negative = find_or_cache_meal_image(
            self.meal,
            "Mensa Garbsen",
            "08.06.2026",
            21600,
            finder=finder,
            now=now + timedelta(hours=7),
        )

        cache_entry = MealImageLookupCache.query.one()

        self.assertIsNone(first)
        self.assertIsNone(fresh_negative)
        self.assertEqual(len(finder.calls), 2)
        self.assertEqual(expired_negative["image_file_id"], IMAGE_ID)
        self.assertTrue(cache_entry.found)

    def test_lookup_recovers_when_parallel_request_inserts_same_cache_key(self):
        now = datetime(2026, 6, 8, tzinfo=timezone.utc)

        def finder(meal_description, mensa_name, selected_date):
            db.session.add(
                MealImageLookupCache(
                    meal_id=self.meal.id,
                    mensa_name=mensa_name,
                    date=selected_date,
                    found=True,
                    image_file_id=RACED_IMAGE_ID,
                    matched_name="Parallel cached result",
                    checked_at=now,
                )
            )
            db.session.commit()
            return {
                "image_file_id": IMAGE_ID,
                "matched_name": meal_description,
            }

        result = find_or_cache_meal_image(
            self.meal,
            "Mensa Garbsen",
            "08.06.2026",
            21600,
            finder=finder,
            now=now,
        )
        cache_entry = MealImageLookupCache.query.one()

        self.assertEqual(result["image_file_id"], IMAGE_ID)
        self.assertEqual(result["matched_name"], self.meal.description)
        self.assertEqual(cache_entry.image_file_id, IMAGE_ID)
        self.assertEqual(cache_entry.matched_name, self.meal.description)


if __name__ == "__main__":
    unittest.main()
