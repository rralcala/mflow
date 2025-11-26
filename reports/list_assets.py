import logging
from datetime import datetime

from data.asset_store import load_assets
from data.internal import exchange_rate


def list_assets(print_pos: bool, print_neg: bool):
    asset_data = {"negatives": [], "positives": [], "currency_summary": []}
    assets = load_assets()
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

        asset_data["currency_summary"].append((k, pval, nval))
        asset_data["return_history"] = returns
    return asset_data
