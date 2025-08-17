from datetime import datetime
import logging
from typing import Tuple, List

from asset_classes.asset import Asset
from lib.gdrive import get_sheet_settings, get_table

FORMAT_STRING = "%m/%d/%Y"


class Payable(Asset):
    def __init__(
        self,
        country: str,
        currency: str,
        description: str,
        amount: float,
        due_date: str,
    ):
        self.country = country
        self.currency = currency
        self.description = description
        self.amount = amount
        self.due_date = due_date

    def get_income(self) -> Tuple[float, str]:
        date = datetime.strptime(self.due_date, FORMAT_STRING)
        if date.month == datetime.now().month and date.year == datetime.now().year:
            return self.amount, self.currency
        return 0.0, "USD"

    def get_current_value(self) -> Tuple[float, str]:
        """
        Returns the value of the payable in its currency.
        """
        return self.amount, self.currency

    def __repr__(self):
        return f"Payable({self.country}, {self.currency}, {self.description}, {self.amount}, {self.due_date})"


def parse_payables(data: List[List[str]]) -> List[Payable]:
    """
    Function to parse account data from the provided data.

    :param data: List of lists containing the account data.
    :return: List of dictionaries with account information.
    """
    parsed_accounts: List[Payable] = []
    for row in data[1:]:  # Skip header row
        if len(row) < 5:
            logging.error("Row {row} does not have enough columns to parse as a Payable.")
        account = Payable(
            country=row[0],
            currency=row[1],
            description=row[2],
            amount=float(row[4].replace(",", "")),
            due_date=row[3],
        )
        logging.debug(f"Parsed Payable: {account}")
        parsed_accounts.append(account)

    return parsed_accounts


def fetch_payables(sheet: str) -> List[Payable]:
    sheet_settings = get_sheet_settings(sheet)

    if "itype" not in sheet_settings or sheet_settings["itype"].lower() != "payable":
        raise ValueError("The first cell of the Summary sheet must be 'Type' and the")

    ac_data = get_table(sheet, sheet_settings["payables_sheet"])
    return parse_payables(ac_data)
