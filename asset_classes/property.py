import logging
from datetime import date, datetime
from typing import List, Tuple

from dateutil.rrule import MONTHLY, rrule

from asset_classes.asset import Asset
from data.datasource import DataSource
from lib.config import DATE_FORMAT_STRING, YEAR


class Property(Asset):
    """Represents a property asset with its attributes and methods to calculate its value."""

    def __init__(
        self,
        country: str,
        currency: str,
        identifier: str,
        purchase_price: float,
        purchase_date: str,
        latest_price: float,
        rented_price: float,
    ):
        self.country = country
        self.currency = currency
        self.identifier = identifier
        self.purchase_price = purchase_price
        self.purchase_date = purchase_date
        self.latest_price = latest_price
        self.rented_price = rented_price
        self.contracts = []

    def get_income(self, today: datetime) -> Tuple[float, str]:
        """
        Returns the income from the property.
        """
        income = self.rented_price
        return income, self.currency

    def get_current_value(self) -> Tuple[float, str]:
        """Returns the current value of the property in its currency."""
        return self.latest_price + self.get_income(datetime.today())[0], self.currency

    def get_liquid_balance(self) -> Tuple[float, str]:
        """
        Returns the liquid balance of the property.
        This method can be overridden by subclasses if needed.
        """
        return 0.0, self.currency

    def get_timeline(self, end: datetime) -> List[Tuple[date, Tuple[float, str]]]:
        timeline = []
        if self.rented_price == 0.0:
            return timeline
        logging.debug(self)
        firsts = list(rrule(MONTHLY, dtstart=datetime.today(), until=end, bymonthday=1))
        for first_of_month in firsts:
            income = self.get_income(first_of_month)
            if income[0] != 0.0:
                timeline.append(
                    (first_of_month.date(), self.get_income(first_of_month))
                )
        return timeline

    def get_currency(self) -> str:
        return self.currency

    def get_returns(self) -> Tuple[float, float]:
        """
        Returns the current value and the annualized return of the asset.
        """
        holding_period_days = (
            datetime.now() - datetime.strptime(self.purchase_date, DATE_FORMAT_STRING)
        ).days
        if holding_period_days > YEAR:
            holding_period_years = holding_period_days / YEAR
            annualized_return = (
                (self.latest_price / self.purchase_price) - 1
            ) / holding_period_years
        else:
            annualized_return = (self.latest_price / self.purchase_price) - 1
        # Assuming rented_price is the mothly rental income
        return self.get_current_value()[0], annualized_return + (
            self.rented_price * 12 / self.latest_price
        )

    def __repr__(self):
        return f"Property({self.identifier}, Latest Price: {self.latest_price}, Currency: {self.currency})"


def get_total_value(properties: List[Property], exchange: float) -> float:
    """
    Returns the total value of the property.
    """
    total = 0.0
    for property in properties:
        if property.currency == "PYG":
            total += property.latest_price / exchange
        else:
            total += property.latest_price
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
            identifier=row[2],
            purchase_price=float(row[3].replace(",", "")),
            purchase_date=row[4],
            latest_price=float(row[5].replace(",", "")),
            rented_price=float(row[6].replace(",", "")),
        )
        parsed_accounts.append(account)

    return parsed_accounts


def fetch(sheet: DataSource) -> List[Property]:
    sheet_settings = sheet.get_sheet_settings()

    if "itype" not in sheet_settings or sheet_settings["itype"].lower() != "property":
        raise ValueError(
            "Can't resolve correct type in sheet. Expected 'property' in 'Type' column."
        )

    ac_data = sheet.get_table(sheet_settings["worksheet"])
    accounts = parse_properties(ac_data)
    return accounts
