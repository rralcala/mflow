import logging
from datetime import datetime

import data.internal
from data.gdrive import list_files_in_folder


def check_history(tpval: float, tnval: float):
    ordered_history = data.internal.read_net_history()

    today = datetime.now()
    new_key = f"{today.month}-{today.year}"
    if len(ordered_history) > 0 and ordered_history[-1][0] == new_key:
        ordered_history.pop()
        data.internal.write_last_net_history(
            str(today.year), str(today.month), tpval + tnval
        )
    ordered_history.append((new_key, tpval + tnval))

    history = -6 if len(ordered_history) > 6 else -len(ordered_history)
    p = ordered_history[history][1]
    x = []
    y = []
    for i in range(history, 0):
        v = ordered_history[i][1]
        logging.info(f"{ordered_history[i][0]}: {v:,.2f} {(v-p):,.2f} USD")

        y.append(v - p)
        x.append(ordered_history[i][0])
        p = v
    return x, y


def list_assets(print_pos: bool, print_neg: bool):
    asset_data = {"negatives": [], "positives": [], "currency_summary": []}
    files = list_files_in_folder()
    if not files:
        raise FileNotFoundError("No files found in the specified Google Drive folder.")

    assets = data.internal.fetch_assets(files)

    exchange = data.internal.exchange_rate("USDPYG")

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
