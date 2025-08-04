import logging
from datetime import date, datetime
from typing import Dict, List

from dateutil.relativedelta import relativedelta
from flask_login import current_user

from asset_classes.asset import Asset
from data.exchange_rates import ExchangeRates
from init import db
from models.history import History
from reports.list_assets import NEGATIVES, POSITIVES, net_worth


def long_term_projection(assets):
    grand_total, b, c = net_worth(assets)
    return grand_total


def list_income(assets: Dict[str, List[Asset]]) -> Dict[str, float]:
    grand_total, b, c = net_worth(assets)
    total_fixed = 0.0
    tot_per_market = {}
    tot_per_location = {}
    inc_per_location = {}

    for currency, asset_list in assets.items():
        for asset in asset_list:
            income_avg = 0.0
            for month in range(0, 12):
                income, currency = asset.get_budgeted_income(
                    datetime.now() + relativedelta(months=month)
                )
                if asset.identifier == "AlquilerPY-Duplex-1":
                    logging.warning(
                        f"Asset {asset.identifier} Month : {month} Income {income} {currency}"
                    )
                income_avg += income
            income_avg = income_avg / 12
            logging.warning(f"Asset {asset.identifier} Income {income_avg} {currency}")
            if currency != "USD":
                usd_value = asset.get_current_value()[0] / ExchangeRates.exchange_rate(
                    f"USD{currency}"
                )
                usd_income = income_avg / ExchangeRates.exchange_rate(f"USD{currency}")
            else:
                usd_income = income_avg
                usd_value = asset.get_current_value()[0]
            total_fixed += usd_income
            tot_per_market.setdefault(asset.get_market(), 0.0)
            tot_per_market[asset.get_market()] += usd_value
            tot_per_location.setdefault(asset.get_location()[1], 0.0)
            tot_per_location[asset.get_location()[1]] += usd_value
            inc_per_location.setdefault(asset.get_location()[1], 0.0)
            inc_per_location[
                asset.get_location()[1]
            ] += usd_income * ExchangeRates.exchange_rate("USDPYG")

    ret = 0.0
    sum_py = 0.0
    sum_us = 0.0
    for current_value, current_return, _, country in b:
        tret = (current_value / grand_total) * current_return
        ret += tret
        if country == "PY":
            sum_py += current_value
        else:
            sum_us += current_value
    debt = 0.0
    capital = 0.0

    for item in c[POSITIVES]:
        amount_str, currency = item[1].split(" ")
        amount = float(amount_str.replace(",", ""))
        if currency != "USD":
            amount = amount / ExchangeRates.exchange_rate(f"USD{currency}")
        capital += amount
    for item in c[NEGATIVES]:
        amount_str, currency = item[1].split(" ")
        amount = float(amount_str.replace(",", ""))
        if currency != "USD":
            amount = amount / ExchangeRates.exchange_rate(f"USD{currency}")
        debt += amount

    if grand_total > 0.0:
        debt_to_assets = -debt / grand_total
    else:
        debt_to_assets = 0.0

    for key, value in tot_per_market.items():
        tot_per_market[key] = value / grand_total
    tot_per_location_pct = []
    for key, value in tot_per_location.items():
        pct = value / grand_total
        # if pct < 0.0 or pct > (0.04 / 100):
        tot_per_location_pct.append((key, value, pct, inc_per_location.get(key, 0.0)))

    resp_dict = {
        "net_worth": grand_total,
        "fixed_income": total_fixed,
        "capital": capital,
        "debt": debt,
        "debt_to_assets": debt_to_assets,
        "return_on_assets": ret,
        "estimated_monthly_income": grand_total * ret / 12,
        "tot_per_market": tot_per_market,
        "tot_per_location": sorted(
            tot_per_location_pct, key=lambda x: x[1], reverse=True
        ),
    }

    return resp_dict


def list_assets(assets: Dict[str, List[Asset]]) -> Dict[str, float]:
    grand_total, returns, c = net_worth(assets)
    total_fixed = 0.0
    tot_per_market = {}
    tot_per_location = {}

    for currency, asset_list in assets.items():
        for asset in asset_list:
            income, currency = asset.get_budgeted_income(datetime.now())
            if currency != "USD":
                usd_value = asset.get_current_value()[0] / ExchangeRates.exchange_rate(
                    f"USD{currency}"
                )
                usd_income = income / ExchangeRates.exchange_rate(f"USD{currency}")
            else:
                usd_income = income
                usd_value = asset.get_current_value()[0]
            total_fixed += usd_income
            tot_per_market.setdefault(asset.get_market(), 0.0)
            tot_per_market[asset.get_market()] += usd_value
            tot_per_location.setdefault(asset.get_location()[1], 0.0)
            tot_per_location[asset.get_location()[1]] += usd_value

    ret = 0.0
    sum_py = 0.0
    sum_us = 0.0
    for current_value, current_return, asset_id, country in returns:

        tret = (current_value / grand_total) * current_return
        ret += tret
        if country == "PY":
            sum_py += current_value
        else:
            sum_us += current_value
    debt = 0.0
    capital = 0.0

    for item in c[POSITIVES]:
        amount_str, currency = item[1].split(" ")
        amount = float(amount_str.replace(",", ""))
        if currency != "USD":
            amount = amount / ExchangeRates.exchange_rate(f"USD{currency}")
        capital += amount
    for item in c[NEGATIVES]:
        amount_str, currency = item[1].split(" ")
        amount = float(amount_str.replace(",", ""))
        if currency != "USD":
            amount = amount / ExchangeRates.exchange_rate(f"USD{currency}")
        debt += amount

    if grand_total > 0.0:
        debt_to_assets = -debt / grand_total
    else:
        debt_to_assets = 0.0

    for key, value in tot_per_market.items():
        tot_per_market[key] = value / grand_total
    tot_per_location_pct = []
    for key, value in tot_per_location.items():
        pct = value / grand_total
        if pct < 0.0 or pct > (0.04 / 100):
            tot_per_location_pct.append((key, value, pct))
    result = History.query.filter_by(
        user_id=int(current_user.id), date=date.today().replace(day=1)
    ).first()
    if not result:
        result = History(
            user_id=int(current_user.id),
            date=date.today().replace(day=1),
            value=round(grand_total, 2),
            fixed=round(total_fixed, 2),
        )
        db.session.add(result)
        db.session.commit()
        logging.warning(
            f"Created new history record for user {current_user.id} with value {grand_total} and fixed {total_fixed}"
        )
    resp_dict = {
        "net_worth": grand_total,
        "fixed_income": total_fixed,
        "capital": capital,
        "debt": debt,
        "debt_to_assets": debt_to_assets,
        "return_on_assets": ret,
        "estimated_monthly_income": grand_total * ret / 12,
        "tot_per_market": tot_per_market,
        "tot_per_location": sorted(
            tot_per_location_pct, key=lambda x: x[1], reverse=True
        ),
    }

    return resp_dict
