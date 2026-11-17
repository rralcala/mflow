import unittest
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from data import asset_store
from data.base import Base
from lib.config import Config
from models.instrument import Instrument
from models.models import Account, Recurrent


class TestLoadAssets(unittest.TestCase):
    """Every model row loads into its asset class with the expected identifier."""

    def setUp(self):
        engine = create_engine("sqlite://")
        self.addCleanup(engine.dispose)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine)
        with self.Session() as session:
            session.add_all(
                [
                    Account(
                        id="Checking",
                        user_id=1,
                        country="US",
                        location="Citi",
                        currency="USD",
                        balance="100",
                        factor="1",
                        account_type="Checking",
                        liquid=1,
                    ),
                    # Another user may use the same name.
                    Account(
                        id="Checking",
                        user_id=2,
                        country="US",
                        location="Bank",
                        currency="USD",
                        balance="5",
                        factor="1",
                        account_type="Checking",
                        liquid=1,
                    ),
                    Instrument(
                        user_id=1,
                        country="US",
                        location="Citi",
                        account="B5894",
                        symbol="USD",
                        factor="1",
                        qty="10",
                        dividend="N",
                        dividend_rate="0",
                        currency="USD",
                        acquisition_date="2026-01-01",
                        acquisition_price="1",
                        liquid=1,
                        capital_rate="0",
                        is_target_pool=1,
                    ),
                    Recurrent(
                        identifier="Rent",
                        user_id=1,
                        country="US",
                        amount="-10",
                        currency="USD",
                        recurrence="0 0 1 * *",
                        start="2026-01-01",
                        end="2030-01-01",
                        flow_class="expense",
                        rate="0",
                        target_asset_id="Citi_B5894_USD",
                    ),
                ]
            )
            session.commit()

    def test_loads_each_type_for_the_user(self):
        user_config = SimpleNamespace(
            USER_ID=1, SECONDARY_CURRENCY="PYG", COINBASE_API_KEY=None
        )
        with patch.object(Config, "DB_SESSION", self.Session, create=True), patch(
            "data.asset_store.ExchangeRates.exchange_rate", return_value=1.0
        ):
            assets = asset_store.load_assets(user_config)["USD"]
        by_id = {asset.get_identifier(): asset for asset in assets}
        self.assertEqual(set(by_id), {"Checking", "Citi_B5894_USD", "Rent"})
        self.assertEqual(by_id["Checking"].get_location(), ("US", "Citi"))
        self.assertEqual(by_id["Checking"].balance, 100.0)
        self.assertEqual(by_id["Citi_B5894_USD"].get_location(), ("US", "Citi"))
        self.assertEqual(by_id["Rent"].target_asset_id, "Citi_B5894_USD")


if __name__ == "__main__":
    unittest.main()
