import unittest
from datetime import datetime
from unittest.mock import patch

from dateutil.relativedelta import relativedelta

from asset_classes.property import Property


class TestPropertyAssets(unittest.TestCase):
    def test_zero_purchase_price_has_no_appreciation(self):
        gift = Property(
            country="US",
            currency="USD",
            identifier="Gift",
            purchase_price=0.0,
            purchase_date=datetime.now().date(),
            latest_price=1200.0,
            rented_price=10.0,
            rent_currency="USD",
            additional_data="",
        )
        self.assertEqual(gift.total_return, 0.1)

    def test_rent_converts_into_the_property_currency(self):
        # A PYG-priced house rented in USD: 100 USD/month is 700,000 PYG.
        house = Property(
            country="PY",
            currency="PYG",
            identifier="Casa",
            purchase_price=84_000_000.0,
            purchase_date=datetime.now().date(),
            latest_price=84_000_000.0,
            rented_price=100.0,
            rent_currency="USD",
            additional_data="",
        )
        with patch(
            "asset_classes.property.ExchangeRates.exchange_rate",
            side_effect=lambda pair: {"USDPYG": 7000.0}[pair],
        ):
            self.assertEqual(house.total_return, 0.1)

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
