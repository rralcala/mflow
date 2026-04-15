import unittest
from datetime import date, datetime

from lib.util import business_days_ago, get_date_4_business_days_ago


class TestBusinessDayHelpers(unittest.TestCase):
    def test_get_date_4_business_days_ago_midweek(self):
        result = get_date_4_business_days_ago(date(2026, 4, 15))
        self.assertEqual(result, date(2026, 4, 9))

    def test_get_date_4_business_days_ago_from_monday(self):
        result = get_date_4_business_days_ago(date(2026, 4, 13))
        self.assertEqual(result, date(2026, 4, 7))

    def test_business_days_ago_accepts_datetime(self):
        result = business_days_ago(4, datetime(2026, 4, 15, 9, 30, 0))
        self.assertEqual(result, date(2026, 4, 9))

    def test_business_days_ago_rejects_negative_days(self):
        with self.assertRaises(ValueError):
            business_days_ago(-1, date(2026, 4, 15))


if __name__ == "__main__":
    unittest.main()
