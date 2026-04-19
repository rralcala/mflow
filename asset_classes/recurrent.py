import calendar
from datetime import date, datetime
from typing import Any, Dict, List, Tuple

from asset_classes.asset import Asset
from data.constants import RecurrentTypes
from data.datasource import DataSource
from lib.config import Config
from lib.logger import get_logger
from lib.util import count_cron_runs, cron_runs
from models import models

Logger = get_logger()


class RecurrentTransaction:
    def __init__(
        self,
        transaction_id: int,
        parent_id: str,
        year_month: str,
        description: str,
        amount: float,
        transaction_date: datetime,
        paid_with: str,
        create_date: datetime,
    ):
        self.transaction_id = transaction_id
        self.parent_id = parent_id
        self.year_month = year_month
        self.description = description
        self.amount = amount
        self.transaction_date = transaction_date
        self.paid_with = paid_with
        self.create_date = create_date


class Recurrent(Asset):
    """Represents a recurrent financial flow with its attributes and methods to calculate its value."""

    def __init__(
        self,
        identifier: str,
        parent_asset_id: str,
        country: str,
        amount: float,
        currency: str,
        recurrence: str,
        start: datetime,
        end: datetime,
        flow_class: str,
        rate: float = 0.0,
    ):
        self.identifier = identifier
        self.amount = amount
        self.country = country
        self.currency = currency
        self.rate = rate
        self.start_date = start
        self.maturity_date = end
        self.recurrence = recurrence
        self.flow_class = flow_class
        self.parent_asset_id = parent_asset_id

    def is_liquid(self) -> bool:
        return False

    def get_location(self):
        return self.country, self.identifier.split("-")[0]

    def get_market(self) -> str:
        return self.currency

    def calculate_year_performance(self):
        """I suspect that recurrents don't have performance, but let's see."""
        return self.get_current_value()[0], self.rate, self.currency

    def get_current_value(self) -> Tuple[float, str]:
        """
        Returns the total value of the recurrent flow.
        """
        paid_amount = 0.0
        if self.flow_class in [RecurrentTypes.Loan, RecurrentTypes.Repayment]:
            paid_amount = (
                count_cron_runs(self.recurrence, self.start_date, self.maturity_date)
                * self.amount
            )
            with Config.DB_SESSION() as session:
                transactions = (
                    session.query(models.RecurrentTransaction)
                    .filter_by(parent_id=self.identifier)
                    .all()
                )
            for row in transactions:
                paid_amount -= float(row.amount)
        return paid_amount, self.currency

    def fetch_transactions(self, date):
        with Config.DB_SESSION() as session:
            select_stmt = session.query(models.RecurrentTransaction).filter_by(
                parent_id=self.identifier, year_month=date.strftime("%Y-%m")
            )
            return session.execute(select_stmt).scalars().all()

    def get_timeline(self, end: datetime) -> List[Tuple[date, Tuple[float, str, bool]]]:
        timeline = []
        start_of_month = datetime.now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        # Switch to items with balance instead of current month
        for date in cron_runs(self.recurrence, start_of_month, end):
            if date >= self.start_date:
                cash_flow = self.amount

                for row in self.fetch_transactions(date):
                    cash_flow -= float(row.amount)
                if self.flow_class == RecurrentTypes.Expense and cash_flow > 0.0:
                    continue
                timeline.append((date.date(), (cash_flow, self.currency, False)))
        return timeline

    def get_returns(self) -> Tuple[float, float]:
        return self.get_current_value()[0], 0.0

    def __repr__(self):
        return f"Recurrent({self.identifier}, Country: {self.country}, Class: {self.flow_class}, Value: {self.amount:,.0f} {self.currency}, Maturity Date: {self.maturity_date.date()}"

    def get_liquid_balance(self) -> Tuple[float, str]:
        """
        Returns the liquid balance of the recurrent flow.
        """
        return 0.0, self.currency

    # Maybe if ran over, go with actual income instead of budgeted?
    def get_budgeted_income(self, year_month: datetime) -> Tuple[float, str]:
        start = year_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        rec_start = self.start_date.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        end = last_date_of_month(year_month)
        cash_flow = 0.0
        if start >= rec_start and end <= self.maturity_date:
            runs = cron_runs(self.recurrence, start, end)
            cash_flow = len(runs) * self.amount
        return cash_flow, self.currency

    def get_actual_income(
        self, year_month: datetime, include_capital=True
    ) -> Tuple[float, str]:
        """
        Returns the income generated by the asset.
        This should calculate whether it's an expense or a loan.
        """
        start = year_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        rec_start = self.start_date.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        end = last_date_of_month(year_month)
        cash_flow = 0.0
        if start >= rec_start and end <= self.maturity_date:
            runs = cron_runs(self.recurrence, start, end)

            for date in runs:
                for row in self.fetch_transactions(date):
                    cash_flow -= float(row.amount)

        return cash_flow, self.currency

    def get_income_balance(self, year_month: datetime) -> Tuple[float, str]:
        income, currency = self.get_actual_income(year_month, include_capital=False)
        budget, _ = self.get_budgeted_income(year_month)
        return (budget + income), currency

    def get_currency(self) -> str:
        return self.currency


def last_date_of_month(today: datetime) -> datetime:
    last_day = calendar.monthrange(today.year, today.month)[1]
    return today.replace(day=last_day)


def parse_recurrent(data: Dict[str, Any]) -> Recurrent:
    """
    Function to parse account data from the provided data.

    :param data: List of lists containing the account data.
    :return: List of dictionaries with account information.
    """
    new_rec = Recurrent(
        identifier=data["identifier"],
        flow_class=data["flow_class"].lower(),
        amount=float(str(data["amount"]).replace(",", "")),
        country=data["country"],
        currency=data["currency"],
        end=data["end"],
        recurrence=data["recurrence"],
        start=data["start"],
        parent_asset_id=data.get("parent_asset", ""),
        rate=data.get("rate", 0.0),
    )

    return new_rec


def fetch(sheet: DataSource) -> Recurrent:
    data = sheet.get_sheet_settings()
    if "itype" not in data or data["itype"].lower() != "recurrent":
        raise ValueError("The first cell of the Summary sheet must be 'itype' and the")

    bond = parse_recurrent(data)

    return bond
