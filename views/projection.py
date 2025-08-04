from datetime import datetime
from typing import Any, Dict, List

from dateutil.relativedelta import relativedelta
from flask_login import current_user

from asset_classes.asset import Asset
from data.exchange_rates import ExchangeRates
from lib.user_config import UserStore
from models.models import Recurrent
from reports.list_assets import net_worth
from reports.pnl import calculate_monthly_pnl_data


def financial_analysis(main_assets: Dict[str, List[Asset]]) -> Dict[str, Any]:

    user_config = UserStore.get_user_config(current_user.id)
    desired_estate = user_config.DESIRED_ESTATE
    net_worth_value, _, _ = net_worth(main_assets)
    last_until_date = datetime.strptime(user_config.LAST_UNTIL, "%Y-%m-%d")
    runway_delta = relativedelta(last_until_date, datetime.now())
    runway = float(runway_delta.years) + float(runway_delta.months) / 12
    exchange = ExchangeRates.exchange_rate("USD" + user_config.SECONDARY_CURRENCY)
    pnl = calculate_monthly_pnl_data(main_assets, months=12, skip_one_off=True)
    current_var = Recurrent.query.get(user_config.DEFAULT_VAR_ID).to_dict()
    current_var_amount = current_var["amount"] / ExchangeRates.exchange_rate(
        f"USD{current_var['currency']}"
    )

    runway_cost = pnl["net"] * runway
    addtitional_monthly_var = (
        (net_worth_value + runway_cost - desired_estate) / runway / 12
    )
    max_var = addtitional_monthly_var + current_var_amount
    result = {
        "net_worth_value": net_worth_value,
        "desired_estate": desired_estate,
        "runway_years": runway,
        "current_year_net": pnl["net"],
        "estimated_max_var_usd": max_var,
        "estimated_max_var_sec_cur": max_var * exchange,
        "secondary_currency": user_config.SECONDARY_CURRENCY,
    }
    return result
