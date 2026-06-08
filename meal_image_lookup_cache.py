from datetime import datetime, timedelta, timezone

from models import MealImageLookupCache, db
from studifutter import find_meal_image, proxied_asset_url


def build_meal_image_payload(image_file_id, matched_name=""):
    return {
        "image_url": proxied_asset_url(image_file_id),
        "thumbnail_url": proxied_asset_url(image_file_id, variant="thumb"),
        "image_file_id": image_file_id,
        "matched_name": matched_name or "",
    }


def find_or_cache_meal_image(
    meal,
    mensa_name,
    selected_date,
    negative_lookup_ttl_seconds,
    finder=find_meal_image,
    now=None,
):
    current_time = now or datetime.now(timezone.utc)
    cache_entry = MealImageLookupCache.query.filter_by(
        meal_id=meal.id,
        mensa_name=mensa_name,
        date=selected_date,
    ).first()

    if cache_entry:
        if cache_entry.found and cache_entry.image_file_id:
            return build_meal_image_payload(
                cache_entry.image_file_id,
                cache_entry.matched_name,
            )
        if _negative_cache_is_fresh(
            cache_entry,
            current_time,
            negative_lookup_ttl_seconds,
        ):
            return None

    image_result = finder(meal.description, mensa_name, selected_date)
    if image_result:
        cache_entry = _upsert_cache_entry(
            cache_entry,
            meal.id,
            mensa_name,
            selected_date,
            found=True,
            image_file_id=image_result["image_file_id"],
            matched_name=image_result.get("matched_name", ""),
            checked_at=current_time,
        )
        db.session.commit()
        return build_meal_image_payload(
            cache_entry.image_file_id,
            cache_entry.matched_name,
        )

    _upsert_cache_entry(
        cache_entry,
        meal.id,
        mensa_name,
        selected_date,
        found=False,
        image_file_id=None,
        matched_name="",
        checked_at=current_time,
    )
    db.session.commit()
    return None


def _negative_cache_is_fresh(cache_entry, current_time, ttl_seconds):
    checked_at = _ensure_aware_datetime(cache_entry.checked_at)
    return current_time - checked_at < timedelta(seconds=ttl_seconds)


def _ensure_aware_datetime(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _upsert_cache_entry(
    cache_entry,
    meal_id,
    mensa_name,
    selected_date,
    found,
    image_file_id,
    matched_name,
    checked_at,
):
    if cache_entry is None:
        cache_entry = MealImageLookupCache(
            meal_id=meal_id,
            mensa_name=mensa_name,
            date=selected_date,
        )
        db.session.add(cache_entry)

    cache_entry.found = found
    cache_entry.image_file_id = image_file_id
    cache_entry.matched_name = matched_name
    cache_entry.checked_at = checked_at
    return cache_entry
