from datetime import date, datetime
from typing import List, Optional, Tuple

from asset_classes.asset import Asset


class Account(Asset):
    """Represents a cash account to manage deposits and withdrawals."""

    def __init__(
        self,
        country: str,
        institution: str,
        identifier: str,
        currency: str,
        balance: float,
        factor: float = 1.0,
        account_type: str = "Savings",
        liquid: bool = True,
        transfer_by: Optional[datetime] = None,
        target_asset_id: str = "",
    ):
        self.country = country
        self.institution = institution
        self._identifier = identifier
        self.currency = currency
        self.balance = balance
        self.factor = factor
        self.account_type = account_type
        self.liquid = liquid
        # Simulations move the whole balance into the target pool on this date.
        self.transfer_by = transfer_by
        self.target_asset_id = target_asset_id

    def get_identifier(self) -> str:
        return self._identifier

    def is_liquid(self) -> bool:
        return self.liquid

    def get_location(self):
        return self.country, self.institution

    def get_market(self) -> str:
        return self.currency

    def calculate_year_performance(self) -> Tuple[float, float, str]:
        return self.get_current_value()[0], 0.0, self.currency

    def get_current_value(self) -> Tuple[float, str]:
        return (self.balance * self.factor), self.currency

    def get_budgeted_income(self, year_month: datetime) -> Tuple[float, str]:
        return 0.0, self.currency

    def get_actual_income(
        self, year_month: datetime, include_capital=True
    ) -> Tuple[float, str]:
        return 0.0, self.currency

    def get_income_balance(self, year_month: datetime) -> Tuple[float, str]:
        return 0.0, self.currency

    def get_liquid_balance(self) -> Tuple[float, str]:
        if self.liquid:
            return self.get_current_value()
        return 0.0, self.currency

    def get_timeline(self, end: datetime) -> List[Tuple[date, Tuple[float, str, bool]]]:
        balance = self.get_liquid_balance()
        if balance[0] == 0.0:
            return []
        return [(datetime.today().date(), (*balance, True))]

    def get_currency(self) -> str:
        return self.currency

    def get_returns(self) -> Tuple[float, float]:
        return self.balance * self.factor, 0.0

    def __repr__(self):
        return f"Account({self._identifier}, {self.institution}, {self.account_type}, Balance: {self.balance:,.0f} {self.currency})"

    def __str__(self):
        return self.__repr__()

    def to_dict(self) -> dict:
        return {
            "country": self.country,
            "institution": self.institution,
            "identifier": self._identifier,
            "currency": self.currency,
            "balance": self.balance,
            "factor": self.factor,
            "account_type": self.account_type,
            "liquid": self.liquid,
        }
