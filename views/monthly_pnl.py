from typing import Dict, List, Tuple

from flask_login import current_user

from asset_classes.asset import Asset
from data.exchange_rates import ExchangeRates
from lib.user_config import UserStore
from reports.pnl import calculate_monthly_pnl_data


def monthly_pnl(
    main_assets: Dict[str, List[Asset]],
    skip_one_off=False,
) -> Tuple[List[Dict], Dict]:
    secondary_currency = UserStore.get_user_config(current_user.id).SECONDARY_CURRENCY
    usd_secondary = ExchangeRates.exchange_rate("USD" + secondary_currency)
    calculation = calculate_monthly_pnl_data(
        main_assets, months=12, skip_one_off=skip_one_off
    )
    year_months = []
    for month_data in calculation["monthly_data"]:

        month = month_data["month"]
        nsums = month_data["expense_sums"]
        psums = month_data["income_sums"]

        expenses = []
        income = []
        for transaction in month_data["expenses"]:
            expenses.append(
                (transaction["assetId"], transaction["amount"], transaction["currency"])
            )
        for transaction in month_data["income"]:
            income.append(
                (transaction["assetId"], transaction["amount"], transaction["currency"])
            )
        year_month = {"month": month, "income": income, "expenses": expenses}
        year_month["income_" + secondary_currency] = psums.get(secondary_currency, 0.0)
        year_month["income_USD"] = psums.get("USD", 0.0)

        year_month["expenses_" + secondary_currency] = nsums.get(
            secondary_currency, 0.0
        )
        year_month["expenses_USD"] = nsums.get("USD", 0.0)

        year_months.append(year_month)

    p_totals = calculation["p_totals"]
    n_totals = calculation["n_totals"]

    summary = {
        "net": [
            p_totals["USD"] + n_totals["USD"],
            p_totals[secondary_currency] + n_totals[secondary_currency],
        ],
        "income": [p_totals["USD"], p_totals[secondary_currency]],
        "expenses": [n_totals["USD"], n_totals[secondary_currency]],
        "secondary_currency": secondary_currency,
    }
    return year_months, summary
