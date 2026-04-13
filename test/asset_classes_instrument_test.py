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
        )
        performance = acc.get_returns()
        self.assertEqual(performance, (1500.0, 0.5))

        acc.acquisition_price = 0
        performance = acc.get_returns()
        self.assertEqual(performance, (1500.0, 0))
