import unittest
from datetime import datetime

from dateutil.relativedelta import relativedelta

from asset_classes.property import Property


class TestPropertyAssets(unittest.TestCase):
    def test_performance(self):
        acc = Property(
            country="US",
            currency="USD",
            identifier="123",
            purchase_price=100.0,
            purchase_date=datetime.now().date(),
            latest_price=110.0,
            rented_price=0.0,
            rent_currency="USD",
            additional_data="",
        )
        performance = acc.get_returns()
        self.assertEqual(performance, (110.0, 0.1))

        acc.purchase_date = datetime.now().date() - relativedelta(years=5)
        performance = acc.get_returns()
        self.assertEqual(performance, (110.0, 0.02))

    def test_performance_with_rent(self):
        acc = Property(
            country="US",
            currency="USD",
            identifier="123",
            purchase_price=100.0,
            purchase_date=datetime.now().date(),
            latest_price=110.0,
            rented_price=1.0,
            rent_currency="USD",
            additional_data="",
        )
        performance = acc.get_returns()
        self.assertEqual(performance, (110.0, 0.2091))

        acc.purchase_date = datetime.now().date() - relativedelta(years=5)
        performance = acc.get_returns()
        self.assertEqual(performance, (110.0, 0.1291))
