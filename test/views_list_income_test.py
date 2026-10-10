import unittest
import unittest.mock
from datetime import datetime

from asset_classes.property import Property
from asset_classes.recurrent import Recurrent
from views.list_assets import list_income


def make_property(identifier, value):
    return Property(
        country="US",
        currency="USD",
        identifier=identifier,
        purchase_price=value,
        purchase_date=datetime(2020, 1, 1).date(),
        latest_price=value,
        rented_price=0.0,
        rent_currency="USD",
        additional_data="",
    )


def make_income(identifier, parent_asset_id, amount):
    return Recurrent(
        identifier=identifier,
        parent_asset_id=parent_asset_id,
        country="US",
        amount=amount,
        currency="USD",
        recurrence="0 0 1 * *",
        start=datetime(2020, 1, 1),
        end=datetime(2040, 1, 1),
        flow_class="income",
    )


class TestListIncomePerLocation(unittest.TestCase):
    def run_report(self, assets):
        with unittest.mock.patch(
            "views.list_assets.ExchangeRates.exchange_rate", return_value=10.0
        ):
            return list_income({"USD": assets})["tot_per_location"]

    def test_child_recurrent_merged_into_parent_location(self):
        house = make_property("Seattle-1", 800.0)
        airbnb = make_income("AIRBNB-SEATTLE-1", "Seattle-1", 120.0)

        # One row for Seattle; monthly income 120 USD at 10 PYG/USD.
        self.assertEqual(
            self.run_report([house, airbnb]), [("Seattle", 800.0, 1.0, 1200.0)]
        )

    def test_recurrent_without_parent_keeps_own_location(self):
        house = make_property("Seattle-1", 800.0)
        rent = make_income("Alquiler-Magallanes-1", "None", 50.0)

        self.assertEqual(
            self.run_report([house, rent]),
            [("Seattle", 800.0, 1.0, 0.0), ("Alquiler", 0.0, 0.0, 500.0)],
        )


if __name__ == "__main__":
    unittest.main()
