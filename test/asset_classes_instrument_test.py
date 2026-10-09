import unittest
from datetime import datetime, time

from asset_classes.instrument import Instrument


class TestInstrumentAssets(unittest.TestCase):
    def test_returns(self):
        acc = Instrument(
            country="US",
            location="NYSE",
            symbol="AAPL",
            price=150.0,
            factor=1.0,
            qty=10,
            estimated_dividend=0.0,
            rate=0.0,
            dividend="",
            currency="USD",
            acquisition_date=datetime.combine(datetime.today(), time.min),
            acquisition_price=100.0,
            liquid=True,
            capital_rate=0.0,
        )
        performance = acc.get_returns()
        self.assertEqual(performance, (1500.0, 0.5))

        acc.acquisition_price = 0
        performance = acc.get_returns()
        self.assertEqual(performance, (1500.0, 0))

    def test_timeline_dividends_match_actual_income(self):
        voo = Instrument(
            country="US",
            location="Citi",
            symbol="VOO",
            price=100.0,
            factor=0.7,
            qty=10,
            estimated_dividend=4.0,
            rate=0.016,
            dividend="0 0 1 1,4,7,10 *",
            currency="USD",
            acquisition_date=datetime(2020, 1, 1),
            acquisition_price=100.0,
            liquid=False,
            capital_rate=0.0,
        )
        today = datetime.today()
        timeline = voo.get_timeline(datetime(today.year + 2, 1, 1))
        dividends = [entry for _, entry in timeline if not entry[2]]

        self.assertTrue(dividends)
        for amount, currency, _ in dividends:
            self.assertAlmostEqual(amount, 2.8)
            self.assertEqual(currency, "USD")
        income, _ = voo.get_actual_income(datetime(today.year + 1, 1, 1))
        self.assertAlmostEqual(income, 2.8)

    def test_returns_with_zero_acquisition_price_held_over_a_year(self):
        old = Instrument(
            country="US",
            location="Gift",
            symbol="X",
            price=10.0,
            factor=1.0,
            qty=10,
            estimated_dividend=0.0,
            rate=0.0,
            dividend="",
            currency="USD",
            acquisition_date=datetime(2020, 1, 1),
            acquisition_price=0.0,
            liquid=True,
            capital_rate=0.0,
        )
        self.assertEqual(old.get_returns(), (100.0, 0.0))
