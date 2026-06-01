import unittest
from datetime import datetime

from menu_refresh import (
    BASELINE_REFRESH_INTERVAL_SECONDS,
    LUNCH_REFRESH_INTERVAL_SECONDS,
    MENU_REFRESH_TIMEZONE,
    calculate_menu_refresh_delay_seconds,
    is_lunch_refresh_window,
)


class MenuRefreshScheduleTest(unittest.TestCase):
    def test_lunch_window_starts_at_11(self):
        now = datetime(2026, 6, 1, 11, 0, tzinfo=MENU_REFRESH_TIMEZONE)

        self.assertTrue(is_lunch_refresh_window(now))
        self.assertEqual(
            calculate_menu_refresh_delay_seconds(now),
            LUNCH_REFRESH_INTERVAL_SECONDS,
        )

    def test_lunch_window_uses_ten_minute_interval(self):
        now = datetime(2026, 6, 1, 12, 30, tzinfo=MENU_REFRESH_TIMEZONE)

        self.assertTrue(is_lunch_refresh_window(now))
        self.assertEqual(
            calculate_menu_refresh_delay_seconds(now),
            LUNCH_REFRESH_INTERVAL_SECONDS,
        )

    def test_lunch_window_ends_at_14(self):
        now = datetime(2026, 6, 1, 14, 0, tzinfo=MENU_REFRESH_TIMEZONE)

        self.assertFalse(is_lunch_refresh_window(now))
        self.assertEqual(
            calculate_menu_refresh_delay_seconds(now),
            BASELINE_REFRESH_INTERVAL_SECONDS,
        )

    def test_outside_lunch_wakes_for_upcoming_lunch_window(self):
        now = datetime(2026, 6, 1, 10, 55, tzinfo=MENU_REFRESH_TIMEZONE)

        self.assertFalse(is_lunch_refresh_window(now))
        self.assertEqual(calculate_menu_refresh_delay_seconds(now), 5 * 60)


if __name__ == "__main__":
    unittest.main()
