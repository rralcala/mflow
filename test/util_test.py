import unittest
from datetime import date, datetime
from unittest.mock import patch

from apiflask.exceptions import HTTPError

from lib.config import Config
from lib.util import (
    PRINTER,
    FormatPrinter,
    business_days_ago,
    count_cron_runs,
    cron_runs,
    normalize_currency,
    recurrence_error,
    require_date,
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


class TestRecurrenceError(unittest.TestCase):
    def test_accepts_at_most_once_a_month(self):
        for pattern in ("0 0 5 * *", "0 0 31 * *", "0 0 30 4,10 *", "0 0 29 2 *"):
            self.assertIsNone(recurrence_error(pattern), pattern)

    def test_rejects_more_than_once_a_month(self):
        for pattern in ("0 0 * * 1", "0 0 1,15 * *", "* * 1 * *", "0 0 29-31 * *"):
            self.assertIn("more than once a month", recurrence_error(pattern))

    def test_rejects_invalid_patterns(self):
        for pattern in (None, "", "N", "0 0 30 2 *"):
            self.assertIn("Invalid recurrence", recurrence_error(pattern))


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


class TestInputValidation(unittest.TestCase):
    def test_normalize_currency_upper_cases_known_codes(self):
        with patch.object(Config, "CURRENCIES", ["usd", "pyg"], create=True):
            self.assertEqual(normalize_currency(" usd "), "USD")
            self.assertEqual(normalize_currency("PYG"), "PYG")

    def test_normalize_currency_rejects_unknown_or_missing(self):
        with patch.object(Config, "CURRENCIES", ["usd"], create=True):
            for value in ("eur", "", None, 5):
                with self.assertRaises(HTTPError) as ctx:
                    normalize_currency(value)
                self.assertEqual(ctx.exception.status_code, 400)

    def test_require_date(self):
        self.assertEqual(require_date("2026-12-15", "dueDate"), "2026-12-15")
        for value in ("12/15/2026", "2026-13-01", "", None):
            with self.assertRaises(HTTPError):
                require_date(value, "dueDate")


if __name__ == "__main__":
    unittest.main()
