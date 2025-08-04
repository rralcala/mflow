from datetime import date, datetime
from typing import List, Tuple

from asset_classes.asset import Asset
from data.datasource import DataSource


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
    ):
        self.country = country
        self.institution = institution
        self.identifier = identifier
        self.currency = currency
        self.balance = balance
        self.factor = factor
        self.account_type = account_type
        self.liquid = liquid

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
            return self.balance, self.currency
        return 0.0, "USD"

    def get_timeline(self, end: datetime) -> List[Tuple[date, Tuple[float, str, bool]]]:
        balance = self.get_liquid_balance()
        if balance[0] == 0.0:
            return []
        return [(datetime.today().date(), (*self.get_liquid_balance(), True))]

    def get_currency(self) -> str:
        return self.currency

    def get_returns(self) -> Tuple[float, float]:
        return self.balance * self.factor, 0.0

    def __repr__(self):
        return f"Account({self.identifier}, {self.institution}, {self.account_type}, Balance: {self.balance:,.0f} {self.currency})"

    def __str__(self):
        return self.__repr__()

    def to_dict(self) -> dict:
        return {
            "country": self.country,
            "institution": self.institution,
            "identifier": self.identifier,
            "currency": self.currency,
            "balance": self.balance,
            "factor": self.factor,
            "account_type": self.account_type,
            "liquid": self.liquid,
        }


def parse_accounts(data: List[List[str]]) -> List[Account]:
    """
    Function to parse account data from the provided data.

    :param data: List of lists containing the account data.
    :return: List of dictionaries with account information.
    """
    parsed_accounts: List[Account] = []
    for row in data[1:]:  # Skip header row
        if len(row) < 9:
            continue  # Skip rows that do not have enough columns
        account = Account(
            country=row[1],
            institution=row[2],
            identifier=row[0],
            currency=row[3],
            balance=float(row[4].replace(",", "")),
            factor=float(row[5].replace(",", "")),
            account_type=row[7],
            liquid=int(row[8]) == 1,
        )
        parsed_accounts.append(account)

    return parsed_accounts


def fetch(sheet: DataSource, worksheet: str):
    """Fetch the asset from Gooogle Sheets"""
    data = sheet.get_sheet_settings()

    if "itype" not in data or data["itype"].lower() != "cash":
        raise ValueError("The first cell of the Summary sheet must be 'Type' and the")

    ac_data = sheet.get_table(worksheet)
    accounts = parse_accounts(ac_data)
    return accounts
