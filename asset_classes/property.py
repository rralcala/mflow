import math
from datetime import date, datetime
from typing import List, Tuple

from asset_classes.asset import Asset
from data.exchange_rates import ExchangeRates
from lib.config import Config


class Property(Asset):
    """Represents a property asset with its attributes and methods to calculate its value."""

    def __init__(
        self,
        country: str,
        currency: str,
        identifier: str,
        purchase_price: float,
        purchase_date: date,
        latest_price: float,
        rented_price: float,
        rent_currency: str,
        additional_data: str,
    ):
        self.country = country
        self.currency = currency
        self._identifier = identifier
        self.purchase_price = purchase_price
        self.purchase_date = purchase_date
        self.latest_price = latest_price
        self.rented_price = rented_price
        self.additional_data = additional_data
        self.rent_currency = rent_currency

    @property
    def total_return(self) -> float:
        days_owned = math.floor(
            (datetime.today().date() - self.purchase_date).total_seconds()
            / float(86400)
        )
        years_owned = days_owned / Config.YEAR
        if years_owned < 1.0:
            years_owned = 1

        annualized_return = (
            (self.latest_price / self.purchase_price) - 1.0
        ) / years_owned
        # Assuming rented_price is the mothly rental income
        rented_price = self.rented_price
        if self.rent_currency != self.currency:
            exchange = ExchangeRates.exchange_rate(f"USD{self.rent_currency}")
            rented_price = self.rented_price / exchange
        if self.latest_price != 0.0:
            rental_return = rented_price * 12 / self.latest_price
        else:
            rental_return = 0
        return round(annualized_return + rental_return, 4)

    def get_identifier(self) -> str:
        return self._identifier

    def is_liquid(self) -> bool:
        return False

    def get_market(self) -> str:
        return "Property" + self.country

    def get_location(self):
        return self.country, self._identifier.split("-")[0]

    def calculate_year_performance(self) -> Tuple[float, float, str]:
        return self.latest_price, self.total_return, self.currency

    def get_income_balance(self, year_month: datetime) -> Tuple[float, str]:
        """
        Rental Income should be added as contract using a Recurrent.
        """
        return 0.0, self.currency

    def get_budgeted_income(self, year_month: datetime) -> Tuple[float, str]:
        """
        Rental Income should be added as contract using a Recurrent.
        """
        return 0.0, self.currency

    def get_actual_income(
        self, year_month: date, include_capital=True
    ) -> Tuple[float, str]:
        """
        Rental Income should be added as contract using a Recurrent.
        """
        return 0.0, self.currency

    def get_current_value(self) -> Tuple[float, str]:
        """Returns the current value of the property in its currency."""
        return (
            self.latest_price + self.get_actual_income(datetime.today().date())[0],
            self.currency,
        )

    def get_liquid_balance(self) -> Tuple[float, str]:
        """
        Returns the liquid balance of the property.
        This method can be overridden by subclasses if needed.
        """
        return 0.0, self.currency

    def get_timeline(self, end: datetime) -> List[Tuple[date, Tuple[float, str, bool]]]:
        return []

    def get_currency(self) -> str:
        return self.currency

    def get_returns(self) -> Tuple[float, float]:
        """
        Returns the current value and the annualized return of the asset.
        """

        return self.get_current_value()[0], self.total_return

    def __repr__(self):
        return f"Property({self._identifier}, Latest Price: {self.latest_price:,.0f} {self.currency})"
