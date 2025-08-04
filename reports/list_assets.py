import logging
from typing import Any, Dict, List, Tuple

from data.exchange_rates import ExchangeRates

POSITIVES = "positives"
NEGATIVES = "negatives"


def list_assets_by_location(assets, print_pos: bool, print_neg: bool) -> Dict[
    str,
    Dict[str, Tuple[str, float, str, str]],
]:
    summary = {}
    for currency, sub in assets.items():

        for asset in sub:
            current_value, currency = asset.get_current_value()
            if current_value == 0.0:
                continue
            if not print_neg and current_value < 0.0:
                continue
            country, location = asset.get_location()
            summary.setdefault(country, {})
            summary[country].setdefault(location, [])
            summary[country][location].append(
                (asset.identifier, current_value, currency, type(asset).__name__)
            )
    return summary


def asset_data_from_asset(asset) -> Dict[str, Any]:
    current_value, currency = asset.get_current_value()
    return {
        "id": asset.identifier,
        "currentValue": current_value,
        "currency": currency,
        "type": type(asset).__name__,
        "details": str(asset),
        "liquid": asset.is_liquid(),
    }


def get_assets(assets, liquid_only: bool) -> List[Dict[str, Any]]:
    response = []
    for currency, sub in assets.items():
        for asset in sub:
            liquid = asset.is_liquid()
            if liquid_only and not liquid:
                continue
            type_name = type(asset).__name__
            if type_name == "Payable" and not asset.commited:
                continue

            response.append(asset_data_from_asset(asset))
    return response


def list_assets(assets, print_pos: bool, print_neg: bool) -> Tuple[
    List[Tuple[str, float, float]],
    List[Tuple[float, float, str, str]],
    Dict[str, List[Tuple[str, str]]],
]:
    asset_data = {NEGATIVES: [], POSITIVES: []}
    currency_summary = []

    returns = []
    for currency, sub in assets.items():
        pval = 0.0
        nval = 0.0
        for asset in sub:
            current_value, currency = asset.get_current_value()
            currval, current_return = asset.get_returns()
            if current_value != currval:
                logging.error(
                    "Current value %s does not match returns value %s for asset %s",
                    current_value,
                    currval,
                    asset.identifier,
                )
            if currency != "USD":
                exchange = ExchangeRates.exchange_rate("USD" + currency)
                returns.append(
                    [
                        current_value / exchange,
                        current_return,
                        asset.identifier,
                        asset.country,
                    ]
                )
            else:
                returns.append(
                    [current_value, current_return, asset.identifier, asset.country]
                )

            if current_value > 0:
                if print_pos:
                    asset_data[POSITIVES].append(
                        (asset.identifier, f"{current_value:,.0f} {currency}")
                    )
                pval += current_value
            elif current_value < 0:
                if print_neg:
                    asset_data[NEGATIVES].append(
                        (asset.identifier, f"{current_value:,.0f} {currency}")
                    )
                nval += current_value
        if currency != "USD":
            exchange = ExchangeRates.exchange_rate("USD" + currency)
            pval /= exchange
            nval /= exchange

        currency_summary.append((currency, pval, nval))
        breakdown = {
            POSITIVES: asset_data[POSITIVES],
            NEGATIVES: asset_data[NEGATIVES],
        }
    return currency_summary, returns, breakdown


def list_asset_performance(assets) -> List[Tuple[str, float, str, float]]:

    performance = []
    for currency, sub in assets.items():

        for asset in sub:
            current_value, current_return, currency = asset.calculate_year_performance()
            if current_value <= 0.0:
                continue
            if currency != "USD":
                exchange = ExchangeRates.exchange_rate("USD" + currency)
                performance.append(
                    [
                        asset.identifier,
                        current_value / exchange,
                        "USD",
                        current_return * 100,
                    ]
                )
            else:
                performance.append(
                    [asset.identifier, current_value, currency, current_return * 100]
                )

    return sorted(performance, key=lambda x: x[3], reverse=True)


def net_worth(assets):
    a, returns, c = list_assets(assets, print_pos=True, print_neg=True)

    grand_total = 0.0
    for item in a:
        grand_total += item[1] + item[2]

    return grand_total, returns, c
