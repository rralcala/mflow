import unittest
from datetime import datetime
from types import SimpleNamespace

from asset_classes.account import Account
from asset_classes.instrument import Instrument
from lib.util import validate_target_asset
from models.instrument import Instrument as InstrumentModel
from models.models import Account as AccountModel
from reports.list_assets import is_target_option


class _Query:
    def __init__(self, rows):
        self.rows = rows

    def filter_by(self, **kwargs):
        return _Query(
            [r for r in self.rows if all(getattr(r, k) == v for k, v in kwargs.items())]
        )

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return self.rows


class _Session:
    def __init__(self, accounts, instruments):
        self.tables = {AccountModel: accounts, InstrumentModel: instruments}

    def query(self, model):
        return _Query(self.tables[model])


def instrument(symbol="USD", is_target_pool=False, liquid=True):
    return Instrument(
        country="US",
        location="Citi",
        symbol=symbol,
        price=1.0,
        factor=1.0,
        qty=100.0,
        estimated_dividend=0.0,
        rate=0.0,
        dividend="",
        currency="USD",
        acquisition_date=datetime(2020, 1, 1),
        acquisition_price=1.0,
        liquid=liquid,
        capital_rate=0.0,
        is_target_pool=is_target_pool,
    )


class TestValidateTargetAsset(unittest.TestCase):
    def setUp(self):
        self.session = _Session(
            accounts=[SimpleNamespace(user_id=1, id="Checking", currency="USD")],
            instruments=[
                SimpleNamespace(
                    user_id=1, location="Puente", symbol="USD", is_target_pool=1
                ),
                SimpleNamespace(
                    user_id=1, location="Citi_B5894", symbol="USD", is_target_pool=0
                ),
            ],
        )

    def test_accounts_are_valid_targets(self):
        self.assertTrue(validate_target_asset(self.session, 1, "Checking", "USD"))

    def test_only_target_pool_instruments_are_valid(self):
        self.assertTrue(validate_target_asset(self.session, 1, "Puente_USD", "USD"))
        self.assertFalse(
            validate_target_asset(self.session, 1, "Citi_B5894_USD", "USD")
        )

    def test_pool_must_hold_the_source_currency(self):
        self.assertFalse(validate_target_asset(self.session, 1, "Puente_USD", "PYG"))


class TestTargetOptions(unittest.TestCase):
    def test_lists_liquid_accounts_and_target_pools_only(self):
        self.assertTrue(is_target_option(Account("US", "Bank", "Checking", "USD", 1.0)))
        self.assertFalse(
            is_target_option(Account("US", "Bank", "Tax", "USD", 1.0, liquid=False))
        )
        self.assertTrue(is_target_option(instrument(is_target_pool=True)))
        self.assertFalse(is_target_option(instrument("VOO", liquid=True)))


if __name__ == "__main__":
    unittest.main()
