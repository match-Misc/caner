import json
import os
import re
import tempfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image, ImageOps, UnidentifiedImageError

from studifutter import directus_asset_api_url, is_directus_file_id


DEFAULT_CACHE_DIR = os.path.join(os.path.dirname(__file__), "data", "meal_images")
DEFAULT_THUMBNAIL_SIZE = 240
DEFAULT_THUMBNAIL_QUALITY = 72
FULL_VARIANT = "full"
THUMB_VARIANT = "thumb"
SUPPORTED_VARIANTS = {FULL_VARIANT, THUMB_VARIANT}

_FORMAT_CONTENT_TYPES = {
    "JPEG": ("image/jpeg", "jpg"),
    "PNG": ("image/png", "png"),
    "WEBP": ("image/webp", "webp"),
    "GIF": ("image/gif", "gif"),
    "BMP": ("image/bmp", "bmp"),
    "TIFF": ("image/tiff", "tiff"),
}


class MealImageCacheError(Exception):
    """Raised when a meal image cannot be cached or served."""


class MealImageCacheInvalidRequest(MealImageCacheError):
    """Raised when a cache request contains an invalid id or variant."""


class MealImageCacheInvalidImage(MealImageCacheError):
    """Raised when an upstream response is not a usable image."""


@dataclass(frozen=True)
class CachedMealImage:
    path: Path
    content_type: str


def get_meal_image_cache_dir():
    return Path(os.environ.get("MEAL_IMAGE_CACHE_DIR", DEFAULT_CACHE_DIR))


def get_thumbnail_size():
    return _bounded_int_env("MEAL_IMAGE_THUMBNAIL_SIZE", DEFAULT_THUMBNAIL_SIZE, 1, 2048)


def get_thumbnail_quality():
    return _bounded_int_env("MEAL_IMAGE_THUMBNAIL_QUALITY", DEFAULT_THUMBNAIL_QUALITY, 1, 95)


def get_cached_studifutter_asset(
    file_id,
    variant=FULL_VARIANT,
    session=None,
    cache_dir=None,
    thumbnail_size=None,
    thumbnail_quality=None,
):
    if not is_directus_file_id(file_id):
        raise MealImageCacheInvalidRequest("Invalid asset id")
    if variant not in SUPPORTED_VARIANTS:
        raise MealImageCacheInvalidRequest("Invalid asset variant")

    root = Path(cache_dir) if cache_dir else get_meal_image_cache_dir()
    if variant == FULL_VARIANT:
        return get_cached_full_asset(file_id, session=session, cache_dir=root)

    return get_cached_thumbnail_asset(
        file_id,
        session=session,
        cache_dir=root,
        thumbnail_size=thumbnail_size,
        thumbnail_quality=thumbnail_quality,
    )


def get_cached_full_asset(file_id, session=None, cache_dir=None):
    root = Path(cache_dir) if cache_dir else get_meal_image_cache_dir()
    metadata = _load_metadata(root, file_id)
    if metadata:
        cached_path = root / "full" / metadata["file_name"]
        if cached_path.exists():
            return CachedMealImage(cached_path, metadata["content_type"])

    payload = _download_image(file_id, session=session)
    content_type, extension = _resolve_image_metadata(
        payload.content,
        payload.content_type,
    )
    file_name = f"{file_id}.{extension}"
    image_path = root / "full" / file_name
    _write_bytes_atomic(image_path, payload.content)
    _write_json_atomic(
        _metadata_path(root, file_id),
        {
            "file_name": file_name,
            "content_type": content_type,
        },
    )
    return CachedMealImage(image_path, content_type)


def get_cached_thumbnail_asset(
    file_id,
    session=None,
    cache_dir=None,
    thumbnail_size=None,
    thumbnail_quality=None,
):
    root = Path(cache_dir) if cache_dir else get_meal_image_cache_dir()
    size = thumbnail_size or get_thumbnail_size()
    quality = thumbnail_quality or get_thumbnail_quality()
    thumbnail_path = root / "thumb" / f"{file_id}_{size}_q{quality}.webp"
    if thumbnail_path.exists():
        return CachedMealImage(thumbnail_path, "image/webp")

    full_asset = get_cached_full_asset(file_id, session=session, cache_dir=root)
    _create_thumbnail(full_asset.path, thumbnail_path, size, quality)
    return CachedMealImage(thumbnail_path, "image/webp")


@dataclass(frozen=True)
class _DownloadedImage:
    content: bytes
    content_type: str


def _download_image(file_id, session=None):
    client = session or requests
    response = client.get(directus_asset_api_url(file_id), timeout=15)
    response.raise_for_status()
    content_type = _clean_content_type(response.headers.get("Content-Type", ""))
    if not content_type.startswith("image/"):
        raise MealImageCacheInvalidImage("Asset is not an image")
    return _DownloadedImage(response.content, content_type)


def _resolve_image_metadata(content, content_type):
    image_format = _validate_image_content(content)
    mapped = _FORMAT_CONTENT_TYPES.get(image_format)
    if mapped:
        return mapped
    return content_type, _extension_from_content_type(content_type)


def _validate_image_content(content):
    try:
        with Image.open(BytesIO(content)) as image:
            image_format = image.format
            image.verify()
    except (OSError, UnidentifiedImageError) as exc:
        raise MealImageCacheInvalidImage("Asset content is not a valid image") from exc

    if not image_format:
        raise MealImageCacheInvalidImage("Asset image format is unknown")
    return image_format.upper()


def _create_thumbnail(source_path, thumbnail_path, size, quality):
    thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=thumbnail_path.parent,
            suffix=".webp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)

        with Image.open(source_path) as image:
            image = ImageOps.exif_transpose(image)
            image.thumbnail((size, size), Image.Resampling.LANCZOS)
            if _has_alpha(image):
                image = image.convert("RGBA")
            else:
                image = image.convert("RGB")
            image.save(temp_path, "WEBP", quality=quality, method=6)

        os.replace(temp_path, thumbnail_path)
    except (OSError, UnidentifiedImageError) as exc:
        if temp_path and temp_path.exists():
            temp_path.unlink()
        raise MealImageCacheInvalidImage("Unable to create image thumbnail") from exc


def _has_alpha(image):
    return image.mode in {"RGBA", "LA"} or "transparency" in image.info


def _load_metadata(root, file_id):
    try:
        with _metadata_path(root, file_id).open(encoding="utf-8") as metadata_file:
            metadata = json.load(metadata_file)
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(metadata, dict):
        return None
    if not metadata.get("file_name") or not metadata.get("content_type"):
        return None
    return metadata


def _metadata_path(root, file_id):
    return root / "metadata" / f"{file_id}.json"


def _write_json_atomic(path, payload):
    _write_bytes_atomic(
        path,
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"),
    )


def _write_bytes_atomic(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(payload)
        os.replace(temp_path, path)
    except OSError as exc:
        if temp_path and temp_path.exists():
            temp_path.unlink()
        raise MealImageCacheError("Unable to write cached meal image") from exc


def _clean_content_type(content_type):
    return content_type.split(";", 1)[0].strip().lower()


def _extension_from_content_type(content_type):
    subtype = content_type.split("/", 1)[1]
    subtype = subtype.split("+", 1)[0].replace("jpeg", "jpg")
    return re.sub(r"[^a-z0-9]+", "", subtype) or "img"


def _bounded_int_env(name, default, minimum, maximum):
    try:
        value = int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, value))
