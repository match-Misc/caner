import json
import os
import re
import time
import unicodedata
from datetime import datetime
from urllib.parse import urljoin

import requests


STUDIFUTTER_API_BASE_URL = os.environ.get(
    "STUDIFUTTER_API_BASE_URL",
    "https://studi-futter.rocket-meals.de/rocket-meals/api",
).rstrip("/")
STUDIFUTTER_REQUEST_TIMEOUT_SECONDS = float(
    os.environ.get("STUDIFUTTER_REQUEST_TIMEOUT_SECONDS", "8")
)
STUDIFUTTER_CANTEEN_CACHE_SECONDS = int(
    os.environ.get("STUDIFUTTER_CANTEEN_CACHE_SECONDS", "3600")
)
DIRECTUS_FILE_ID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

_canteen_cache = {"loaded_at": 0, "items": []}


class StudiFutterError(Exception):
    """Raised when StudiFutter data cannot be fetched or interpreted."""


def normalize_meal_name(value):
    if not value:
        return ""

    normalized = unicodedata.normalize("NFKC", str(value)).casefold()
    normalized = normalized.replace("\u00a0", " ")
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"\s*,\s*", ", ", normalized)
    return normalized.strip()


def parse_caner_date(date_value):
    return datetime.strptime(date_value, "%d.%m.%Y").date().isoformat()


def is_directus_file_id(file_id):
    return bool(file_id and DIRECTUS_FILE_ID_PATTERN.match(str(file_id)))


def directus_asset_api_url(file_id):
    if not is_directus_file_id(file_id):
        raise ValueError("Invalid Directus file id")
    return f"{STUDIFUTTER_API_BASE_URL}/assets/{file_id}"


def proxied_asset_url(file_id, variant="full"):
    if not is_directus_file_id(file_id):
        return ""
    asset_url = f"/api/studifutter/assets/{file_id}"
    if variant == "thumb":
        return f"{asset_url}?variant=thumb"
    if variant == "full":
        return f"{asset_url}?variant=full"
    return asset_url


def get_studifutter_json(path, params=None, session=None):
    client = session or requests
    url = urljoin(f"{STUDIFUTTER_API_BASE_URL}/", path.lstrip("/"))
    response = client.get(
        url,
        params=params or {},
        timeout=STUDIFUTTER_REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise StudiFutterError("Unexpected StudiFutter response")
    return payload


def get_studifutter_canteens(session=None, now=None):
    current_time = time.time() if now is None else now
    if (
        _canteen_cache["items"]
        and current_time - _canteen_cache["loaded_at"] < STUDIFUTTER_CANTEEN_CACHE_SECONDS
    ):
        return _canteen_cache["items"]

    payload = get_studifutter_json(
        "/items/canteens",
        params={"fields": "id,alias,external_identifier", "limit": "-1"},
        session=session,
    )
    canteens = payload.get("data") or []
    if not isinstance(canteens, list):
        raise StudiFutterError("Unexpected StudiFutter canteen list")

    _canteen_cache["loaded_at"] = current_time
    _canteen_cache["items"] = canteens
    return canteens


def resolve_studifutter_canteen_id(mensa_name, session=None):
    target = normalize_meal_name(mensa_name)
    if not target:
        return None

    for canteen in get_studifutter_canteens(session=session):
        aliases = [
            canteen.get("alias"),
            canteen.get("external_identifier"),
        ]
        if target in {normalize_meal_name(alias) for alias in aliases if alias}:
            return canteen.get("id")
    return None


def build_foodoffers_filter(canteen_id, iso_date):
    return {
        "_and": [
            {"canteen": {"_eq": canteen_id}},
            {
                "_or": [
                    {
                        "_and": [
                            {"date": {"_gte": iso_date}},
                            {"date": {"_lte": iso_date}},
                        ]
                    },
                    {"date": {"_null": True}},
                ]
            },
        ]
    }


def get_foodoffers_for_canteen_date(canteen_id, iso_date, session=None):
    fields = ",".join(
        [
            "id",
            "alias",
            "date",
            "food.id",
            "food.alias",
            "food.image",
            "food.image_remote_url",
            "food.translations.languages_code",
            "food.translations.name",
        ]
    )
    payload = get_studifutter_json(
        "/items/foodoffers",
        params={
            "fields": fields,
            "limit": "-1",
            "filter": json.dumps(build_foodoffers_filter(canteen_id, iso_date)),
        },
        session=session,
    )
    offers = payload.get("data") or []
    if not isinstance(offers, list):
        raise StudiFutterError("Unexpected StudiFutter foodoffer list")
    return offers


def iter_offer_names(offer):
    alias = offer.get("alias")
    if alias:
        yield alias

    food = offer.get("food") or {}
    food_alias = food.get("alias")
    if food_alias:
        yield food_alias

    for translation in food.get("translations") or []:
        language_code = translation.get("languages_code") or ""
        if language_code.split("-")[0] not in {"de", "en"}:
            continue
        name = translation.get("name")
        if name:
            yield name


def find_matching_foodoffer(offers, meal_description):
    target = normalize_meal_name(meal_description)
    if not target:
        return None

    for offer in offers:
        candidate_names = {normalize_meal_name(name) for name in iter_offer_names(offer)}
        if target in candidate_names:
            return offer
    return None


def image_response_from_offer(offer):
    food = offer.get("food") or {}
    image_file_id = food.get("image")
    image_url = proxied_asset_url(image_file_id)
    if not image_url:
        return None

    return {
        "image_url": image_url,
        "thumbnail_url": proxied_asset_url(image_file_id, variant="thumb"),
        "image_file_id": image_file_id,
        "matched_name": food.get("alias") or offer.get("alias") or "",
    }


def find_meal_image(meal_description, mensa_name, caner_date, session=None):
    iso_date = parse_caner_date(caner_date)
    canteen_id = resolve_studifutter_canteen_id(mensa_name, session=session)
    if not canteen_id:
        return None

    offers = get_foodoffers_for_canteen_date(canteen_id, iso_date, session=session)
    offer = find_matching_foodoffer(offers, meal_description)
    if not offer:
        return None

    return image_response_from_offer(offer)
