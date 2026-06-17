import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from PIL import Image

from meal_image_cache import (
    MealImageCacheInvalidImage,
    MealImageCacheInvalidRequest,
    get_cached_studifutter_asset,
)


IMAGE_ID = "4ff2b6bf-1239-4a2b-ade2-73196977b777"


class FakeImageResponse:
    def __init__(self, content, content_type="image/png"):
        self.content = content
        self.headers = {"Content-Type": content_type}

    def raise_for_status(self):
        return None


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, timeout=None):
        self.calls.append({"url": url, "timeout": timeout})
        return self.responses.pop(0)


def make_png_bytes():
    buffer = BytesIO()
    image = Image.new("RGB", (32, 24), color=(255, 0, 0))
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class MealImageCacheTest(unittest.TestCase):
    def test_cache_miss_downloads_once_and_cache_hit_avoids_upstream(self):
        session = FakeSession([FakeImageResponse(make_png_bytes())])

        with tempfile.TemporaryDirectory() as cache_dir:
            first = get_cached_studifutter_asset(
                IMAGE_ID,
                session=session,
                cache_dir=cache_dir,
            )
            second = get_cached_studifutter_asset(
                IMAGE_ID,
                session=session,
                cache_dir=cache_dir,
            )
            with Image.open(first.path) as image:
                image_format = image.format
                image_size = image.size

        self.assertEqual(len(session.calls), 1)
        self.assertEqual(first.content_type, "image/webp")
        self.assertEqual(second.content_type, "image/webp")
        self.assertEqual(first.path.name, second.path.name)
        self.assertTrue(first.path.name.endswith("_full_q88.webp"))
        self.assertEqual(image_format, "WEBP")
        self.assertEqual(image_size, (32, 24))

    def test_thumbnail_generation_creates_cached_webp(self):
        session = FakeSession([FakeImageResponse(make_png_bytes())])

        with tempfile.TemporaryDirectory() as cache_dir:
            thumbnail = get_cached_studifutter_asset(
                IMAGE_ID,
                variant="thumb",
                session=session,
                cache_dir=cache_dir,
                thumbnail_size=20,
                thumbnail_quality=70,
            )
            cached_again = get_cached_studifutter_asset(
                IMAGE_ID,
                variant="thumb",
                session=session,
                cache_dir=cache_dir,
                thumbnail_size=20,
                thumbnail_quality=70,
            )

            with Image.open(thumbnail.path) as image:
                image_format = image.format
                image_size = image.size

            self.assertTrue(Path(cache_dir, "full").exists())

        self.assertEqual(len(session.calls), 1)
        self.assertEqual(thumbnail.content_type, "image/webp")
        self.assertEqual(cached_again.path, thumbnail.path)
        self.assertEqual(image_format, "WEBP")
        self.assertLessEqual(max(image_size), 20)

    def test_legacy_cached_full_asset_is_migrated_to_full_size_webp(self):
        with tempfile.TemporaryDirectory() as cache_dir:
            root = Path(cache_dir)
            legacy_path = root / "full" / f"{IMAGE_ID}.png"
            legacy_path.parent.mkdir(parents=True)
            legacy_path.write_bytes(make_png_bytes())
            metadata_path = root / "metadata" / f"{IMAGE_ID}.json"
            metadata_path.parent.mkdir(parents=True)
            metadata_path.write_text(
                json.dumps(
                    {
                        "content_type": "image/png",
                        "file_name": legacy_path.name,
                    }
                ),
                encoding="utf-8",
            )

            migrated = get_cached_studifutter_asset(
                IMAGE_ID,
                session=FakeSession([]),
                cache_dir=cache_dir,
            )

            with Image.open(migrated.path) as image:
                image_format = image.format
                image_size = image.size

        self.assertEqual(migrated.content_type, "image/webp")
        self.assertNotEqual(migrated.path.name, legacy_path.name)
        self.assertEqual(image_format, "WEBP")
        self.assertEqual(image_size, (32, 24))

    def test_invalid_content_type_is_rejected(self):
        session = FakeSession([FakeImageResponse(b"not an image", "text/plain")])

        with tempfile.TemporaryDirectory() as cache_dir:
            with self.assertRaises(MealImageCacheInvalidImage):
                get_cached_studifutter_asset(
                    IMAGE_ID,
                    session=session,
                    cache_dir=cache_dir,
                )

    def test_invalid_variant_is_rejected(self):
        with tempfile.TemporaryDirectory() as cache_dir:
            with self.assertRaises(MealImageCacheInvalidRequest):
                get_cached_studifutter_asset(
                    IMAGE_ID,
                    variant="giant",
                    cache_dir=cache_dir,
                )


if __name__ == "__main__":
    unittest.main()
