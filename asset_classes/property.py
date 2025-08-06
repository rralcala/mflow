import logging
from typing import List

from g_tools import get_table, get_sheet_settings, USDPYG


class Property:

    def __init__(
        self,
        country: str,
        currency: str,
        property_id: str,
        purchase_price: float,
        purchase_date: str,
        latest_price: float,
        rented_price: float,
    ):
        self.country = country
        self.currency = currency
        self.property_id = property_id
        self.purchase_price = purchase_price
        self.purchase_date = purchase_date
        self.latest_price = latest_price
        self.rented_price = rented_price
    def __repr__(self):
        return f"Properties({self.__dict__})"
    def get_income(self):
        """
        Returns the income from the property.
        """
        return self.rented_price, self.currency

def get_total_value(properties: List[Property]) -> float:
    """
    Returns the total value of the property.
    """
    total = 0.0
    for property in properties:
        if property.currency == "PYG":
            total += property.latest_price / USDPYG
            #logging.debug(f"{property.property_id} = {property.latest_price / USDPYG}")
        else:
            total += property.latest_price
            #logging.debug(f"{property.property_id} = {property.latest_price}")
    return total

def parse_properties(data: List[List[str]]) -> List[Property]:
    """
    Function to parse account data from the provided data.

    :param data: List of lists containing the account data.
    :return: List of dictionaries with account information.
    """
    parsed_accounts: List[Property] = []
    for row in data[1:]:  # Skip header row
        if len(row) < 6:
            continue  # Skip rows that do not have enough columns
        account = Property(
            country=row[0],
            currency=row[1],
            property_id=row[2],
            purchase_price=float(row[3].replace(",", "")),
            purchase_date=row[4],
            latest_price=float(row[5].replace(",", "")),
            rented_price=float(row[6].replace(",", "")),
        )
        parsed_accounts.append(account)

    return parsed_accounts


def fetch_properties(sheet: str) -> List[Property]:
    sheet_settings = get_sheet_settings(sheet)

    if "itype" not in sheet_settings or sheet_settings["itype"].lower() != "property":
        raise ValueError(
            "Can't resolve correct type in sheet. Expected 'property' in 'Type' column."
        )

    ac_data = get_table(sheet, sheet_settings["worksheet"])
    accounts = parse_properties(ac_data)
    return accounts
