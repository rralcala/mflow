from datetime import datetime, date
from typing import Any, Dict, List, Tuple
import logging

from asset_classes.asset import Asset
from data.db import Transactions
from data.gdrive import get_sheet_settings, get_table
from lib.config import DATE_FORMAT_STRING


class DepositCertificate(Asset):
    """Represents a financial asset with its attributes and methods to calculate its value."""

    def __init__(
        self,
        identifier: str,
        capital: float,
        currency: str,
        maturity: str,
        country: str,
        itype: str,
        entity: str,
        interest_rate: float,
        interest_schedule: List[Dict[str, Any]],
    ):
        self.identifier = identifier
        self.capital = capital
        self.currency = currency
        self.maturity = maturity
        self.country = country
        self.type = itype
        self.entity = entity
        self.interest_rate = interest_rate
        self.interest_schedule: List[Dict[str, Any]] = interest_schedule

    def get_current_value(self) -> Tuple[float, str]:
        """
        Returns the value of the asset in USD.
        """
        return self.capital, self.currency

    def __repr__(self):
        return (
            f"DepositCertificate(entity={self.identifier},"
            f" capital={self.capital}, currency={self.currency})"
        )

    def get_returns(self) -> Tuple[float, float]:
        return self.capital, self.interest_rate

    def get_liquid_balance(self) -> Tuple[float, str]:
        return 0.0, self.currency

    def get_timeline(self, end: datetime) -> List[Tuple[date, Tuple[float, str]]]:
        timeline = []
        for payment in self.interest_schedule:
            payment_date = datetime.strptime(payment["date"], DATE_FORMAT_STRING)
            if payment_date <= end and payment["paid"] != "1":
                timeline.append((payment_date.date(), (payment["amount"], self.currency)))
        maturity_datetime = datetime.strptime(self.maturity, DATE_FORMAT_STRING)
        if maturity_datetime <= end:
            logging.debug(f"Adding maturity payment on {maturity_datetime.date()} for {self.identifier}")
            timeline.append((maturity_datetime.date(), (self.capital, self.currency)))
        return timeline

    def get_income(self, today: datetime) -> Tuple[float, str]:
        total = 0.0
        maturity_date = datetime.strptime(self.maturity, DATE_FORMAT_STRING)
        if maturity_date.month == today.month and maturity_date.year == today.year:
            total += self.capital
        for d in self.interest_schedule:
            date = datetime.strptime(d["date"], "%m/%d/%Y")
            if date.month == today.month and date.year == today.year:
                total += d["amount"]
        t = Transactions()
        identified = t.get(self.identifier, today.year, today.month)
        # logging.debug(len(identified))
        for v in identified:
            total += v["amount"]
        return total, self.currency

    def get_currency(self) -> str:
        return self.currency


def fetch(sheet: str) -> DepositCertificate:
    data = get_sheet_settings(sheet)

    if "itype" not in data or data["itype"] != "CD":
        raise ValueError("The first cell of the Summary sheet must be 'Type' and the")

    ac_data = get_table(sheet, data["interest_schedule"])
    interest: List[Dict[str, Any]] = []

    for row in ac_data[1:]:  # Skip header row
        interest.append(
            {
                "seq": row[0],
                "date": row[1],
                "amount": float(row[2].replace(",", "")),
                "paid": row[3],
            }
        )
    try:
        cd = DepositCertificate(
            identifier=data["identifier"],
            capital=float(data["capital"].replace(",", "")),
            currency=data["currency"],
            interest_rate=float(data["rate"].replace("%", "")) / 100,
            maturity=data["maturity"],
            country=data["country"],
            itype=data["itype"],
            entity=data["entity"],
            interest_schedule=interest,
        )
    except KeyError as e:
        raise ValueError(f"Missing required field in sheet {sheet}: {e}")
    return cd
