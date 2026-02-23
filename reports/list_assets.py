import logging
from typing import Dict, List, Tuple

from data.internal import exchange_rate


def list_assets(assets, print_pos: bool, print_neg: bool) -> Tuple[
    List[Tuple[str, float, float]],
    List[Tuple[float, float, str]],
    Dict[str, List[Tuple[str, str]]],
]:
    asset_data = {"negatives": [], "positives": []}
    currency_summary = []
    exchange = exchange_rate("USDPYG")

    returns = []
    for k, sub in assets.items():
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
            if k == "PYG":
                returns.append(
                    [current_value / exchange, current_return, asset.identifier]
                )
            else:
                returns.append([current_value, current_return, asset.identifier])

            if current_value > 0:
                if print_pos:
                    asset_data["positives"].append(
                        (asset.identifier, f"{current_value:,.0f} {currency}")
                    )
                pval += current_value
            elif current_value < 0:
                if print_neg:
                    asset_data["negatives"].append(
                        (asset.identifier, f"{current_value:,.0f} {currency}")
                    )
                nval += current_value
        if k == "PYG":
            pval /= exchange
            nval /= exchange

        currency_summary.append((k, pval, nval))
        breakdown = {
            "postives": asset_data["positives"],
            "negatives": asset_data["negatives"],
        }
    return currency_summary, returns, breakdown


def list_asset_performance(assets) -> List[Tuple[str, float, str, float]]:

    exchange = exchange_rate("USDPYG")

    performance = []
    for k, sub in assets.items():

        for asset in sub:
            current_value, current_return, currency = asset.calculate_year_performance()
            if current_value <= 0.0:
                continue
            if k == "PYG":
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
