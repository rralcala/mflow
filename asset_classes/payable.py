from datetime import date, datetime
from typing import List, Tuple

from asset_classes.asset import Asset


class Payable(Asset):
    """A single future-dated payment, repeated yearly unless one_off.

    Only `balance` (what is still owed or due) is used in calculations.
    `amount` is informational: it documents the full size of the payment,
    which can be much larger than what's left once part of it is paid.
    """

    def __init__(
        self,
        country: str,
        currency: str,
        identifier: str,
        amount: float,
        balance: float,
        due_date: datetime,
        commited: bool,
        one_off: bool,
        flow_class: str,
        target_asset_id: str = "",
    ):
        self.country = country
        self.currency = currency
        self._identifier = identifier
        self.amount = amount
        self.flow_class = flow_class
        self.balance = balance
        self.due_date = due_date
        self.commited = commited
        self.one_off = one_off
        self.target_asset_id = target_asset_id

    def get_identifier(self) -> str:
        return self._identifier

    def is_liquid(self) -> bool:
        return False

    def get_market(self) -> str:
        return self.currency

    def get_location(self):
        return self.country, self._identifier.split("-")[0]

    def calculate_year_performance(self) -> Tuple[float, float, str]:
        return self.balance, 0.0, self.currency

    def get_budgeted_income(self, today: datetime) -> Tuple[float, str]:
        date = self.due_date.replace(day=1)

        balance = 0.0
        if date.month == today.month and date.year == today.year:
            balance = self.balance

        return balance, self.currency

    def get_income_balance(self, today: datetime) -> Tuple[float, str]:
        date = self.due_date.replace(day=1)

        balance = 0.0
        if date.month == today.month and date.year == today.year:
            balance = self.balance

        return balance, self.currency

    def get_actual_income(self, year_month, include_capital=True):
        """Payments made so far aren't tracked: amount is informational only."""
        return 0.0, self.currency

    def get_liquid_balance(self) -> Tuple[float, str]:
        """
        Returns the liquid balance of the payable.
        This method can be overridden by subclasses if needed.
        """
        return 0.0, self.currency

    def get_timeline(self, end: datetime) -> List[Tuple[date, Tuple[float, str, bool]]]:
        due_date_date = self.due_date.date()
        if end.date() >= due_date_date:
            return [(due_date_date, (self.balance, self.currency, False))]
        else:
            return []

    def get_current_value(self) -> Tuple[float, str]:
        """
        Returns the value of the payable in its currency.
        Treat commited entries as NW.
        """
        if self.commited:
            return self.balance, self.currency
        else:
            return 0.0, self.currency

    def get_currency(self) -> str:
        return self.currency

    def get_returns(self) -> Tuple[float, float]:
        if self.commited:  # TODO and it's due
            return self.balance, 0.0
        return 0.0, 0.0

    def __repr__(self):
        return f"Payable({self._identifier}, {self.country}, {self.balance:,.0f} {self.currency}, {self.due_date})"
