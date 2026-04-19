from datetime import datetime
from typing import Any, Dict, Generator, List, Tuple

from dateutil.relativedelta import relativedelta
from flask_login import current_user

from asset_classes.asset import Asset
from data.exchange_rates import ExchangeRates
from lib.logger import get_logger
from lib.user_config import UserStore

Logger = get_logger()


class IncomeField:
    AMOUNT = 0
    CURRENCY = 1


def monthly_transactions(
    main_assets: Dict[str, List[Asset]], months=12, balance=False, skip_one_off=False
) -> Generator[Tuple[str, List[Dict[str, Any]]], None]:
    start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    fake_id = 0
    for _ in range(months):
        year_month = start.strftime("%Y-%m")
        transactions: List[Dict[str, Any]] = []
        for assets in main_assets.values():

            for asset in assets:
                # If skip one offs and asset has one_off set to True, skip it
                if skip_one_off and getattr(asset, "one_off", False):
                    continue
                if balance:
                    income = asset.get_income_balance(start)
                else:
                    income = asset.get_budgeted_income(start)
                if (
                    income[IncomeField.AMOUNT] > -0.01
                    and income[IncomeField.AMOUNT] < 0.01
                ):
                    continue
                transactions.append(
                    {
                        "id": year_month + "-" + asset.identifier,
                        "assetId": asset.identifier,
                        "amount": income[IncomeField.AMOUNT],
                        "currency": income[IncomeField.CURRENCY],
                    }
                )
                fake_id += 1
        yield year_month, transactions
        start = start + relativedelta(months=1)


def calculate_monthly_pnl_data(
    main_assets: Dict[str, List[Asset]],
    months: int = 12,
    skip_one_off: bool = False, summary_only: bool = False,
) -> Dict[str, Any]:
    secondary_currency = UserStore.get_user_config(current_user.id).SECONDARY_CURRENCY
    usd_secondary = ExchangeRates.exchange_rate("USD" + secondary_currency)
    p_totals = {"USD": 0.0, secondary_currency: 0.0}
    n_totals = {"USD": 0.0, secondary_currency: 0.0}
    monthly_data = []

    for month, transactions in monthly_transactions(
        main_assets, months=months, skip_one_off=skip_one_off
    ):
        nsums = {"USD": 0.0, secondary_currency: 0.0}
        psums = {"USD": 0.0, secondary_currency: 0.0}
        month_income = []
        month_expenses = []

        for transaction in transactions:
            currency = transaction["currency"]

            if transaction["amount"] < 0.0:
                month_expenses.append(transaction)
                nsums[currency] += round(transaction["amount"], 2)
            elif transaction["amount"] > 0.0:
                month_income.append(transaction)
                psums[currency] += round(transaction["amount"], 2)

        p_totals[secondary_currency] += psums.get(secondary_currency, 0.0)
        n_totals[secondary_currency] += nsums.get(secondary_currency, 0.0)
        p_totals["USD"] += psums.get("USD", 0.0)
        n_totals["USD"] += nsums.get("USD", 0.0)
        if not summary_only:
            monthly_data.append(
                {
                    "month": month,
                    "income": month_income,
                    "expenses": month_expenses,
                    "income_sums": psums,
                    "expense_sums": nsums,
                }
        )

    return {
        "monthly_data": monthly_data,
        "p_totals": p_totals,
        "n_totals": n_totals,
    }
