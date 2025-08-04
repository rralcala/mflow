from datetime import datetime
from typing import Any, Dict, List

from dateutil.relativedelta import relativedelta
from flask_login import current_user

from asset_classes.asset import Asset
from asset_classes.payable import Payable
from asset_classes.recurrent import Recurrent
from data.exchange_rates import ExchangeRates
from lib.user_config import UserStore


def spending_analysis(main_assets: Dict[str, List[Asset]]) -> Dict[str, Any]:
    user_config = UserStore.get_user_config(current_user.id)
    payables: List[Payable] = []
    recurrents: List[Recurrent] = []
    for _, assets in main_assets.items():
        for asset in assets:
            if isinstance(asset, Payable):
                if asset.one_off:
                    continue
                payables.append(asset)
            elif isinstance(asset, Recurrent):
                recurrents.append(asset)
    total_budget = {}
    now = datetime.now()
    for _ in range(0, 12):
        now = now + relativedelta(months=1)
        for payable in payables:
            budget, currency = payable.get_budgeted_income(now)
            if currency != "USD":
                exchange = ExchangeRates.exchange_rate(f"USD{currency}")
            else:
                exchange = 1.0
            budget_usd = budget / exchange
            total_budget.setdefault(payable.flow_class, 0)
            total_budget[payable.flow_class] += budget_usd

        for recurrent in recurrents:
            budget, currency = recurrent.get_budgeted_income(now)
            if currency != "USD":
                exchange = ExchangeRates.exchange_rate(f"USD{currency}")
            else:
                exchange = 1.0
            budget_usd = budget / exchange
            total_budget.setdefault(recurrent.flow_class, 0)
            total_budget[recurrent.flow_class] += budget_usd
    for key in total_budget.keys():
        total_budget[key] = total_budget[key] / 12
    result = "<table><tr><th>Flow Class</th><th  style='text-align: right;'>Monthly Spending</th><th  style='text-align: right;'>Secondary Currency</th></tr>"
    exchange = ExchangeRates.exchange_rate(f"USD{user_config.SECONDARY_CURRENCY}")
    result = {
        "exchange": exchange,
        "total_budget": total_budget,
        "secondary_currency": user_config.SECONDARY_CURRENCY,
    }
    return result
