import logging
from datetime import date, datetime
from typing import List, Tuple

from asset_classes.asset import Asset
from data.db import Transactions
from data.gdrive import get_sheet_settings, get_table
from lib.config import DATE_FORMAT_STRING


class Payable(Asset):
    def __init__(
        self,
        country: str,
        currency: str,
        identifier: str,
        amount: float,
        due_date: str,
        commited: bool,
    ):
        self.country = country
        self.currency = currency
        self.identifier = identifier
        self.amount = amount
        self.due_date = due_date
        self.commited = commited

    def get_income(self, today: datetime) -> Tuple[float, str]:
        date = datetime.strptime(self.due_date, DATE_FORMAT_STRING).replace(day=1)

        if date <= today:
            t = Transactions()
            amount = self.amount
            for v in t.get(self.identifier, "", ""):
                amount += v["amount"]

            return amount, self.currency
        return 0.0, self.currency

    def get_liquid_balance(self) -> Tuple[float, str]:
        """
        Returns the liquid balance of the payable.
        This method can be overridden by subclasses if needed.
        """
        return 0.0, self.currency

    def get_timeline(self, end: datetime) -> List[Tuple[date, Tuple[float, str]]]:
        due_date_date = datetime.strptime(self.due_date, DATE_FORMAT_STRING).date()
        if end.date() >= due_date_date:
            return [(due_date_date, (self.amount, self.currency))]
        else:
            return []

    def get_current_value(self) -> Tuple[float, str]:
        """
        Returns the value of the payable in its currency.
        """
        if self.commited:
            return self.amount, self.currency
        else:
            return 0.0, self.currency

    def get_currency(self) -> str:
        return self.currency

    def get_returns(self) -> Tuple[float, float]:
        if self.commited:  # TODO and it's due
            # t = Transactions()
            amount = self.amount
            # for v in t.get(self.identifier, today.year, today.month):
            #    amount += v["amount"]
            return self.amount, 0.0
        return 0.0, 0.0

    def __repr__(self):
        return f"Payable({self.country}, {self.currency}, {self.identifier}, {self.amount}, {self.due_date})"


def parse_payables(data: List[List[str]]) -> List[Payable]:
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
            amount=float(row[4].replace(",", "")),
            due_date=row[3],
            commited=row[5].strip() == "1",
        )
        logging.debug(f"Parsed Payable: {account}")
        parsed_accounts.append(account)

    return parsed_accounts


def fetch(sheet: str) -> List[Payable]:
    sheet_settings = get_sheet_settings(sheet)

    if "itype" not in sheet_settings or sheet_settings["itype"].lower() != "payable":
        raise ValueError("The first cell of the Summary sheet must be 'Type' and the")

    ac_data = get_table(sheet, sheet_settings["payables_sheet"])
    return parse_payables(ac_data)
