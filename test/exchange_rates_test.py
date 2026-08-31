import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import requests

from data.exchange_rates import ExchangeRates
from lib.config import Config


class _SessionContext:
    def __init__(self, session):
        self._session = session

    def __enter__(self):
        return self._session

    def __exit__(self, exc_type, exc, tb):
        return False


class _UnlockedLock:
    def locked(self):
        return False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _LockedLock:
    def locked(self):
        return True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestExchangeRates(unittest.TestCase):
    def setUp(self):
        ExchangeRates.quote_cache = {}
        ExchangeRates.currencies = {"usd", "eur", "mxn"}
        ExchangeRates.last_update = datetime.min

    def test_is_stale_or_empty_true_when_cache_empty(self):
        ExchangeRates.quote_cache = {}
        self.assertTrue(ExchangeRates.is_stale_or_empty())

    def test_is_stale_or_empty_true_when_cache_stale(self):
        ExchangeRates.quote_cache = {"USDEUR": 0.91}
        ExchangeRates.last_update = datetime(2026, 4, 19, 10, 0, 0)

        class FixedDateTime(datetime):
            @classmethod
            def now(cls):
                return datetime(2026, 4, 19, 11, 5, 1)

        with patch("data.exchange_rates.datetime", FixedDateTime):
            self.assertTrue(ExchangeRates.is_stale_or_empty())

    def test_is_stale_or_empty_false_when_cache_fresh(self):
        ExchangeRates.quote_cache = {"USDEUR": 0.91}
        ExchangeRates.last_update = datetime(2026, 4, 19, 11, 0, 0)

        class FixedDateTime(datetime):
            @classmethod
            def now(cls):
                return datetime(2026, 4, 19, 11, 30, 0)

        with patch("data.exchange_rates.datetime", FixedDateTime):
            self.assertFalse(ExchangeRates.is_stale_or_empty())

    def test_refresh_currency_data_populates_cache_and_updates_timestamp(self):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"usd": {"eur": 0.9174, "mxn": 17.123}}

        def fake_ticker(symbol):
            prices = {
                "btc-USD": 66666.123456,
                "AAPL": 205.987,
                "IAUM": 100.1234,
            }
            return SimpleNamespace(fast_info={"last_price": prices[symbol]})

        class FixedDateTime(datetime):
            @classmethod
            def now(cls):
                return datetime(2026, 4, 19, 12, 0, 0)

        with patch("data.exchange_rates.requests.get", return_value=response), patch(
            "data.exchange_rates.yf.Ticker", side_effect=fake_ticker
        ), patch.object(Config, "TRADED_CRYPTO", ["btc"], create=True), patch.object(
            Config, "TRADED_STOCKS", ["AAPL"], create=True
        ), patch.object(
            Config, "TRADED_METALS", ["IAUM"], create=True
        ), patch(
            "data.exchange_rates.datetime", FixedDateTime
        ):
            ExchangeRates._refresh_currency_data()

        self.assertEqual(ExchangeRates.quote_cache["USDEUR"], 0.92)
        self.assertEqual(ExchangeRates.quote_cache["USDMXN"], 17.12)
        self.assertEqual(ExchangeRates.quote_cache["BTCUSD"], 66666.1235)
        self.assertEqual(ExchangeRates.quote_cache["AAPL"], 205.99)
        self.assertEqual(ExchangeRates.last_update, datetime(2026, 4, 19, 12, 0, 0))

    def test_refresh_currency_data_raises_request_exception(self):
        with patch(
            "data.exchange_rates.requests.get",
            side_effect=requests.RequestException("network down"),
        ), patch.object(Config, "TRADED_CRYPTO", [], create=True), patch.object(
            Config, "TRADED_STOCKS", [], create=True
        ):
            with self.assertRaises(requests.RequestException):
                ExchangeRates._refresh_currency_data()

    def test_latest_in_db_returns_min_when_no_records(self):
        query_result = MagicMock()
        query_result.scalar.return_value = None
        session = MagicMock()
        session.query.return_value = query_result

        with patch.object(
            Config, "DB_SESSION", lambda: _SessionContext(session), create=True
        ):
            self.assertEqual(ExchangeRates.latest_in_db(), datetime.min)

    def test_latest_in_db_parses_string_date(self):
        query_result = MagicMock()
        query_result.scalar.return_value = "2026-04-19"
        session = MagicMock()
        session.query.return_value = query_result

        with patch.object(
            Config, "DB_SESSION", lambda: _SessionContext(session), create=True
        ):
            self.assertEqual(
                ExchangeRates.latest_in_db(), datetime(2026, 4, 19, 0, 0, 0)
            )

    def test_local_quotes_on_returns_symbol_value_pairs(self):
        quote_a = SimpleNamespace(symbol="USDEUR", value="0.91234")
        quote_b = SimpleNamespace(symbol="BTCUSD", value="66000.12999")
        query_result = MagicMock()
        query_result.filter.return_value.all.return_value = [quote_a, quote_b]
        session = MagicMock()
        session.query.return_value = query_result

        with patch.object(
            Config, "DB_SESSION", lambda: _SessionContext(session), create=True
        ):
            result = ExchangeRates.local_quotes_on("2026-04-19")

        self.assertEqual(result, [("USDEUR", 0.9123), ("BTCUSD", 66000.13)])

    def test_ensure_currency_data_returns_immediately_when_locked(self):
        with patch("data.exchange_rates.FX_FETCH_LOCK", _LockedLock()), patch.object(
            ExchangeRates, "fetch_from_local"
        ) as from_local, patch.object(
            ExchangeRates, "_refresh_currency_data"
        ) as refresh:
            ExchangeRates.ensure_currency_data()

        from_local.assert_not_called()
        refresh.assert_not_called()

    def test_ensure_currency_data_refreshes_when_local_is_empty(self):
        ExchangeRates.quote_cache = {}

        with patch("data.exchange_rates.FX_FETCH_LOCK", _UnlockedLock()), patch.object(
            ExchangeRates, "fetch_from_local"
        ) as from_local, patch.object(
            ExchangeRates, "_refresh_currency_data"
        ) as refresh:
            ExchangeRates.ensure_currency_data()

        from_local.assert_called_once()
        refresh.assert_called_once()

    def test_ensure_currency_data_skips_refresh_when_local_fills_cache(self):
        ExchangeRates.quote_cache = {}

        def populate_cache():
            ExchangeRates.quote_cache["USDEUR"] = 0.9

        with patch("data.exchange_rates.FX_FETCH_LOCK", _UnlockedLock()), patch.object(
            ExchangeRates, "fetch_from_local", side_effect=populate_cache
        ) as from_local, patch.object(
            ExchangeRates, "_refresh_currency_data"
        ) as refresh:
            ExchangeRates.ensure_currency_data()

        from_local.assert_called_once()
        refresh.assert_not_called()

    def test_fetch_from_local_loads_quotes_into_cache(self):
        ExchangeRates.quote_cache = {}
        Config.CURRENCIES = ["usd"]
        with patch.object(
            ExchangeRates, "latest_in_db", return_value=datetime(2026, 4, 19, 0, 0, 0)
        ), patch.object(
            ExchangeRates,
            "local_quotes_on",
            return_value=[("USDEUR", 0.91), ("BTCUSD", 67000.0)],
        ):
            ExchangeRates.fetch_from_local()

        self.assertEqual(ExchangeRates.quote_cache["USDEUR"], 0.91)
        self.assertEqual(ExchangeRates.quote_cache["BTCUSD"], 67000.0)

    def test_exchange_rate_returns_one_for_base_currency(self):
        ExchangeRates.currencies = {"usd", "eur"}

        with patch.object(ExchangeRates, "ensure_currency_data") as ensure_data:
            result = ExchangeRates.exchange_rate("USD")

        ensure_data.assert_called_once()
        self.assertEqual(result, 1.0)

    def test_exchange_rate_returns_cached_rate(self):
        ExchangeRates.quote_cache = {"USDEUR": 0.91}

        with patch.object(ExchangeRates, "ensure_currency_data") as ensure_data:
            result = ExchangeRates.exchange_rate("USDEUR")

        ensure_data.assert_called_once()
        self.assertEqual(result, 0.91)

    def test_exchange_rate_raises_when_missing(self):
        ExchangeRates.quote_cache = {}
        ExchangeRates.currencies = {"usd"}

        with patch.object(ExchangeRates, "ensure_currency_data"):
            with self.assertRaises(ValueError):
                ExchangeRates.exchange_rate("USDCAD")

    def test_get_all_returns_cache_and_ensures_data(self):
        ExchangeRates.quote_cache = {"USDEUR": 0.91}

        with patch.object(ExchangeRates, "ensure_currency_data") as ensure_data:
            result = ExchangeRates.get_all()

        ensure_data.assert_called_once()
        self.assertEqual(result, {"USDEUR": 0.91})


if __name__ == "__main__":
    unittest.main()
