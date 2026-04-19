import unittest
from datetime import datetime

from asset_classes.bond import Bond
from lib.config import Config


class TestBondAsset(unittest.TestCase):
    def setUp(self):
        self.bond = Bond(
            identifier="BOND-1",
            capital=1000.0,
            interest_rate=0.05,
            maturity_date=datetime(2026, 12, 31),
            currency="USD",
            country="US",
            entity="Treasury",
        )

    def test_init_sets_expected_attributes(self):
        self.assertEqual(self.bond.identifier, "BOND-1")
        self.assertEqual(self.bond.capital, 1000.0)
        self.assertEqual(self.bond.interest_rate, 0.05)
        self.assertEqual(self.bond.maturity_date, datetime(2026, 12, 31))
        self.assertEqual(self.bond.currency, "USD")
        self.assertEqual(self.bond.country, "US")
        self.assertEqual(self.bond.entity, "Treasury")
        self.assertEqual(self.bond.payment_schedule, [])

    def test_is_liquid_returns_false(self):
        self.assertFalse(self.bond.is_liquid())

    def test_get_market_returns_currency(self):
        self.assertEqual(self.bond.get_market(), "USD")

    def test_get_location_returns_country_and_entity(self):
        self.assertEqual(self.bond.get_location(), ("US", "Treasury"))

    def test_calculate_year_performance_returns_current_value_rate_and_currency(self):
        self.assertEqual(self.bond.calculate_year_performance(), (1000.0, 0.05, "USD"))

    def test_get_liquid_balance_returns_zero_and_currency(self):
        self.assertEqual(self.bond.get_liquid_balance(), (0.0, "USD"))

    def test_get_timeline_returns_unpaid_payments_and_maturity(self):
        self.bond.payment_schedule = [
            {"date": datetime(2026, 1, 10), "amount": 20.0, "paid": False},
            {"date": datetime(2026, 1, 15), "amount": 20.0, "paid": True},
            {"date": datetime(2027, 1, 10), "amount": 20.0, "paid": False},
        ]

        timeline = self.bond.get_timeline(datetime(2026, 12, 31))

        self.assertEqual(
            timeline,
            [
                (datetime(2026, 1, 10).date(), (20.0, "USD", False)),
                (datetime(2026, 12, 31).date(), (1000.0, "USD", True)),
            ],
        )

    def test_get_timeline_excludes_maturity_when_end_before_maturity(self):
        timeline = self.bond.get_timeline(datetime(2026, 12, 30))
        self.assertEqual(timeline, [])

    def test_get_returns_returns_capital_and_rate(self):
        self.assertEqual(self.bond.get_returns(), (1000.0, 0.05))

    def test_get_budgeted_income_sums_payments_for_month(self):
        self.bond.payment_schedule = [
            {"date": datetime(2026, 4, 5), "amount": 10.0, "paid": False},
            {"date": datetime(2026, 4, 15), "amount": 20.0, "paid": True},
            {"date": datetime(2026, 5, 1), "amount": 30.0, "paid": False},
        ]

        self.assertEqual(
            self.bond.get_budgeted_income(datetime(2026, 4, 1)),
            (30.0, "USD"),
        )

    def test_get_actual_income_includes_paid_and_optionally_capital(self):
        self.bond.payment_schedule = [
            {"date": datetime(2026, 12, 5), "amount": 10.0, "paid": True},
            {"date": datetime(2026, 12, 15), "amount": 20.0, "paid": False},
        ]

        with_capital = self.bond.get_actual_income(datetime(2026, 12, 1))
        without_capital = self.bond.get_actual_income(
            datetime(2026, 12, 1), include_capital=False
        )

        self.assertEqual(with_capital, (1010.0, "USD"))
        self.assertEqual(without_capital, (10.0, "USD"))

    def test_get_income_balance_includes_unpaid_and_optionally_capital(self):
        self.bond.payment_schedule = [
            {"date": datetime(2026, 12, 5), "amount": 10.0, "paid": True},
            {"date": datetime(2026, 12, 15), "amount": 20.0, "paid": False},
        ]

        with_capital = self.bond.get_income_balance(datetime(2026, 12, 1))
        without_capital = self.bond.get_income_balance(
            datetime(2026, 12, 1), include_capital=False
        )

        self.assertEqual(with_capital, (1020.0, "USD"))
        self.assertEqual(without_capital, (20.0, "USD"))

    def test_get_current_value_returns_capital_and_currency(self):
        self.assertEqual(self.bond.get_current_value(), (1000.0, "USD"))

    def test_get_currency_returns_currency(self):
        self.assertEqual(self.bond.get_currency(), "USD")

    def test_repr_formats_identifier_capital_rate_and_maturity(self):
        result = repr(self.bond)
        expected = (
            "Bond(BOND-1, Face Value:1,000 USD, Interest Rate: 5.00%, "
            "Maturity Date: 2026-12-31)"
        )
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
