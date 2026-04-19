import unittest
from datetime import date, datetime
from unittest.mock import patch

from lib.util import (
    PRINTER,
    FormatPrinter,
    business_days_ago,
    count_cron_runs,
    cron_runs,
    sha256_hash,
)


class TestFormatPrinter(unittest.TestCase):
    def test_format_uses_custom_float_format(self):
        formatted, readable, recursive = PRINTER.format(1234.5, {}, 0, 0)
        self.assertEqual(formatted, "1,234.50")
        self.assertEqual(readable, 1)
        self.assertEqual(recursive, 0)

    def test_format_falls_back_for_unmapped_type(self):
        printer = FormatPrinter({float: "{:.1f}"})
        formatted, _, _ = printer.format("hello", {}, 0, 0)
        self.assertEqual(formatted, "'hello'")


class TestCronHelpers(unittest.TestCase):
    def test_cron_runs_returns_occurrences_within_window(self):
        start = datetime(2026, 4, 1, 0, 0, 0)
        end = datetime(2026, 4, 3, 23, 59, 59)

        runs = cron_runs("0 0 * * *", start, end)

        self.assertEqual(
            runs,
            [
                datetime(2026, 4, 1, 0, 0, 0),
                datetime(2026, 4, 2, 0, 0, 0),
                datetime(2026, 4, 3, 0, 0, 0),
            ],
        )

    def test_cron_runs_returns_empty_for_short_pattern(self):
        start = datetime(2026, 4, 1, 0, 0, 0)
        end = datetime(2026, 4, 3, 23, 59, 59)

        self.assertEqual(cron_runs("", start, end), [])

    def test_count_cron_runs_matches_generated_occurrences(self):
        start = datetime(2026, 4, 1, 0, 0, 0)
        end = datetime(2026, 4, 5, 23, 59, 59)

        self.assertEqual(count_cron_runs("0 0 * * *", start, end), 5)


class TestSha256Hash(unittest.TestCase):
    def test_sha256_hash_known_value(self):
        self.assertEqual(
            sha256_hash("hello"),
            "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
        )


class TestBusinessDayHelpers(unittest.TestCase):
    def test_business_days_ago_zero_days_returns_same_date(self):
        result = business_days_ago(0, date(2026, 4, 15))
        self.assertEqual(result, date(2026, 4, 15))

    def test_business_days_ago_from_monday_skips_weekend(self):
        result = business_days_ago(4, date(2026, 4, 13))
        self.assertEqual(result, date(2026, 4, 7))

    def test_business_days_ago_uses_current_date_when_from_date_is_none(self):
        fixed_now = datetime(2026, 4, 20, 8, 0, 0)

        class FixedDateTime(datetime):
            @classmethod
            def now(cls):
                return fixed_now

        with patch("lib.util.datetime", FixedDateTime):
            result = business_days_ago(1)

        self.assertEqual(result, date(2026, 4, 17))

    def test_business_days_ago_rejects_negative_days(self):
        with self.assertRaises(ValueError):
            business_days_ago(-1, date(2026, 4, 15))


if __name__ == "__main__":
    unittest.main()
