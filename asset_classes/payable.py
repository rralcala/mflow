import logging
from datetime import date, datetime
from typing import Any, List, Tuple

from asset_classes.asset import Asset
from data.datasource import DataSource


class Payable(Asset):
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
    ):
        self.country = country
        self.currency = currency
        self.identifier = identifier
        self.amount = amount
        self.flow_class = flow_class
        self.balance = balance
        self.due_date = due_date
        self.commited = commited
        self.one_off = one_off

    def is_liquid(self) -> bool:
        return False

    def get_market(self) -> str:
        return self.currency

    def get_location(self):
        return self.country, self.identifier.split("-")[0]

    def calculate_year_performance(self) -> Tuple[float, float, str]:
        return self.balance, 0.0, self.currency

    def get_budgeted_income(self, today: datetime) -> Tuple[float, str]:
        date = self.due_date.replace(day=1)

        balance = 0.0
        if date.month == today.month and date.year == today.year:
            balance = self.amount

        return balance, self.currency

    def get_income_balance(self, today: datetime) -> Tuple[float, str]:
        date = self.due_date.replace(day=1)

        balance = 0.0
        if date.month == today.month and date.year == today.year:
            balance = self.balance

        return balance, self.currency

    def get_actual_income(self, year_month, include_capital=True):
        budget, currency = self.get_budgeted_income(year_month)
        balance, _ = self.get_income_balance(year_month)
        return (budget - balance), currency

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
        return f"Payable({self.identifier}, {self.country}, {self.balance:,.0f} {self.currency}, {self.due_date})"


def parse_payables(data: List[List[Any]]) -> List[Payable]:
    """
    Function to parse account data from the provided data.

    :param data: List of lists containing the account data.
    :return: List of dictionaries with account information.
    """
    parsed_accounts: List[Payable] = []
    for row in data[1:]:  # Skip header row
        if len(row) < 6:
            logging.error(
                "Row {row} does not have enough columns to parse as a Payable."
            )
        account = Payable(
            country=row[0],
            currency=row[1],
            identifier=row[2],
            amount=float(row[4]),
            due_date=row[3],
            commited=int(row[5]) == 1,
            balance=float(row[4]),
            one_off=False,
            flow_class="expense",
        )

        parsed_accounts.append(account)

    return parsed_accounts


def fetch(sheet: DataSource) -> List[Payable]:
    sheet_settings = sheet.get_sheet_settings()

    if "itype" not in sheet_settings or sheet_settings["itype"].lower() != "payable":
        raise ValueError("The first cell of the Summary sheet must be 'Type' and the")

    ac_data = sheet.get_table(sheet_settings["payables_sheet"])
    return parse_payables(ac_data)
