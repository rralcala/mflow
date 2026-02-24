import logging
from typing import Dict, List, Tuple

from data.internal import exchange_rate

POSITIVES = "positives"
NEGATIVES = "negatives"


def list_assets(assets, print_pos: bool, print_neg: bool) -> Tuple[
    List[Tuple[str, float, float]],
    List[Tuple[float, float, str]],
    Dict[str, List[Tuple[str, str]]],
]:
    asset_data = {NEGATIVES: [], POSITIVES: []}
    currency_summary = []
    exchange = exchange_rate("USDPYG")

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
            if currency == "PYG":
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
        if currency == "PYG":
            pval /= exchange
            nval /= exchange

        currency_summary.append((currency, pval, nval))
        breakdown = {
            POSITIVES: asset_data[POSITIVES],
            NEGATIVES: asset_data[NEGATIVES],
        }
    return currency_summary, returns, breakdown


def list_asset_performance(assets) -> List[Tuple[str, float, str, float]]:
    exchange = exchange_rate("USDPYG")
    performance = []
    for currency, sub in assets.items():

        for asset in sub:
            current_value, current_return, currency = asset.calculate_year_performance()
            if current_value <= 0.0:
                continue
            if currency == "PYG":
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
