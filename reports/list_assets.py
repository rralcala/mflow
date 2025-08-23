from datetime import datetime
from typing import Sequence
import logging

from asset_classes.fetcher import fetch_if_not_cached
from data.gdrive import list_files_in_folder
import data.internal


def check_history(tpval: float, tnval: float):
    ordered_history = data.internal.read_net_history()

    today = datetime.now()
    new_key = f"{today.month}-{today.year}"
    if ordered_history[-1][0] == new_key:
        ordered_history.pop()
    ordered_history.append((new_key, tpval + tnval))

    data.internal.write_net_history(ordered_history)
    p = ordered_history[-6][1]
    x = []
    y = []
    for i in range(-6, 0):
        v = ordered_history[i][1]
        logging.info(f"{ordered_history[i][0]}: {v:,.2f} {(v-p):,.2f} USD")

        y.append(v - p)
        x.append(ordered_history[i][0])
        p = v
    return x, y



def fetch_assets(files):
    items = {"USD": [], "PYG": []}
    for file in files:
        logging.debug("Fetching asset data for %s", file)
        fetched = fetch_if_not_cached(file)
        if isinstance(fetched, Sequence):
            for sub_item in fetched:
                items[sub_item.get_currency()].append(sub_item)
        else:
            items[fetched.get_currency()].append(fetched)
    return items


def list_assets(print_pos: bool, print_neg: bool):
    files = list_files_in_folder()
    if not files:
        raise FileNotFoundError("No files found in the specified Google Drive folder.")

    assets = fetch_assets(files)

    logging.debug("Fetched %i assets:", len(assets))
    exchange = data.internal.exchange_rate("USDPYG")
    tpval = 0.0
    tnval = 0.0
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
                    logging.info(
                    "Positive asset found: %s with value %s %s",
                    asset.identifier,
                    f"{current_value:,.0f}",
                    currency,
                )
                pval += current_value
            elif current_value < 0:
                if print_neg:
                    logging.info(
                    f"Negative asset found: {asset.identifier} with value {current_value:,.0f} {currency}"
                )
                nval += current_value
        if k == "PYG":
            pval /= exchange
            nval /= exchange
        tpval += pval
        tnval += nval

        logging.info(
        f"Positive value: {pval:,.2f}USD in {k}, Negative value: {nval:,.2f}USD in {k}"
    )
    return tpval, tnval, returns
