from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


MENU_REFRESH_TIMEZONE = ZoneInfo("Europe/Berlin")
LUNCH_REFRESH_START_HOUR = 11
LUNCH_REFRESH_END_HOUR = 14
LUNCH_REFRESH_INTERVAL_SECONDS = 10 * 60
BASELINE_REFRESH_INTERVAL_SECONDS = 6 * 60 * 60


def to_menu_refresh_local_time(now=None):
    """Return an aware datetime in the menu refresh timezone."""
    if now is None:
        return datetime.now(MENU_REFRESH_TIMEZONE)
    if now.tzinfo is None:
        return now.replace(tzinfo=MENU_REFRESH_TIMEZONE)
    return now.astimezone(MENU_REFRESH_TIMEZONE)


def is_lunch_refresh_window(now=None):
    local_now = to_menu_refresh_local_time(now)
    return (
        LUNCH_REFRESH_START_HOUR
        <= local_now.hour
        < LUNCH_REFRESH_END_HOUR
    )


def seconds_until_next_lunch_window(now=None):
    local_now = to_menu_refresh_local_time(now)
    next_lunch_start = local_now.replace(
        hour=LUNCH_REFRESH_START_HOUR,
        minute=0,
        second=0,
        microsecond=0,
    )
    if local_now >= next_lunch_start:
        next_lunch_start += timedelta(days=1)
    return max(1, int((next_lunch_start - local_now).total_seconds()))


def calculate_menu_refresh_delay_seconds(now=None):
    if is_lunch_refresh_window(now):
        return LUNCH_REFRESH_INTERVAL_SECONDS
    return min(
        BASELINE_REFRESH_INTERVAL_SECONDS,
        seconds_until_next_lunch_window(now),
    )
