from datetime import datetime
from typing import List, Tuple

from asset_classes.asset import Asset
from lib.gdrive import get_sheet_settings, get_table


class Account(Asset):
    """Represents a financial account with its attributes and methods to manage deposits and withdrawals."""

    def __init__(
        self,
        country: str,
        institution: str,
        identifier: str,
        currency: str,
        balance: float,
        factor: float = 1.0,
        account_type: str = "Savings",
    ):
        self.country = country
        self.institution = institution
        self.identifier = identifier
        self.currency = currency
        self.balance = balance
        self.factor = factor
        self.account_type = account_type

    def get_current_value(self) -> Tuple[float, str]:
        return (self.balance * self.factor), self.currency

    def get_income(self, today: datetime) -> Tuple[float, str]:
        return 0.0, self.currency

    def get_liquid_balance(self) -> Tuple[float, str]:
        if (
            self.account_type.lower() == "savings"
            or self.account_type.lower() == "checking"
        ):
            return self.balance, self.currency
        return 0.0, "USD"

    def get_currency(self) -> str:
        return self.currency

    def get_returns(self) -> Tuple[float, float]:
        return self.balance * self.factor, 0.0

    def __repr__(self):
        return f"Account({self.identifier}, Balance: {self.balance}, Currency: {self.currency})"

    def __str__(self):
        return self.__repr__()


def parse_accounts(data: List[List[str]]) -> List[Account]:
    """
    Function to parse account data from the provided data.

    :param data: List of lists containing the account data.
    :return: List of dictionaries with account information.
    """
    parsed_accounts: List[Account] = []
    for row in data[1:]:  # Skip header row
        if len(row) < 8:
            continue  # Skip rows that do not have enough columns
        account = Account(
            country=row[0],
            institution=row[1],
            identifier=row[2],
            currency=row[3],
            balance=float(row[4].replace(",", "")),
            factor=float(row[5].replace(",", "")),
            account_type=row[7],
        )
        parsed_accounts.append(account)

    return parsed_accounts


def fetch(sheet: str, worksheet: str):
    data = get_sheet_settings(sheet)

    if "itype" not in data or data["itype"].lower() != "cash":
        raise ValueError("The first cell of the Summary sheet must be 'Type' and the")

    ac_data = get_table(sheet, worksheet)
    accounts = parse_accounts(ac_data)
    return accounts
