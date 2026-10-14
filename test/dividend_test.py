import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from apiflask import HTTPError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from data import asset_store
from data.base import Base
from lib.config import Config
from lib.util import require_dividend
from models.instrument import Instrument as InstrumentModel


class TestRequireDividend(unittest.TestCase):
    def test_no_dividend_or_cron_pattern(self):
        self.assertEqual(require_dividend("N"), "N")
        self.assertEqual(require_dividend(" n "), "N")
        self.assertEqual(require_dividend("0 0 1 * *"), "0 0 1 * *")
        self.assertEqual(require_dividend(" 0 0 28 3,6,9,12 * "), "0 0 28 3,6,9,12 *")
        # Leap-day schedules fire, just not every year.
        self.assertEqual(require_dividend("0 0 29 2 *"), "0 0 29 2 *")

    def test_anything_else_is_a_400(self):
        for value in (None, "", " ", "No", "monthly", "0 0 1 *", 5, "0 0 30 2 *"):
            with self.subTest(value=value), self.assertRaises(HTTPError) as ctx:
                require_dividend(value)
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertIn("dividend", ctx.exception.message)


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 10, 14)


class TestLoadAssetsDividend(unittest.TestCase):
    def load(self, dividend):
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        db_session = sessionmaker(bind=engine)
        with db_session() as session:
            session.add(
                InstrumentModel(
                    user_id=1,
                    country="US",
                    location="Citi",
                    symbol="VOO",
                    factor="1",
                    qty="10",
                    dividend=dividend,
                    dividend_rate="0.12",
                    currency="USD",
                    acquisition_date="2026-01-01",
                    acquisition_price="1",
                    liquid=1,
                    capital_rate="0",
                )
            )
            session.commit()
        user_config = SimpleNamespace(
            USER_ID=1, SECONDARY_CURRENCY="PYG", COINBASE_API_KEY=None
        )
        with patch.object(Config, "DB_SESSION", db_session, create=True), patch(
            "data.asset_store.ExchangeRates.exchange_rate", return_value=100.0
        ), patch("data.asset_store.datetime", FixedDateTime):
            (instrument,) = asset_store.load_assets(user_config)["USD"]
        return instrument

    def test_monthly_dividend_is_split_across_payouts(self):
        # 10 shares * 100 * 12% a year, paid 12 times.
        self.assertAlmostEqual(self.load("0 0 1 * *").estimated_dividend, 10.0)

    def test_year_without_payouts_has_no_dividend(self):
        # Regression: 2026 has no Feb 29, so payouts was 0 and loading raised
        # ZeroDivisionError.
        self.assertEqual(self.load("0 0 29 2 *").estimated_dividend, 0.0)

    def test_no_dividend(self):
        self.assertEqual(self.load("N").estimated_dividend, 0.0)


if __name__ == "__main__":
    unittest.main()
