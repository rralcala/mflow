from datetime import datetime
import logging

from asset_classes.fetcher import fetch_if_not_cached
from data.gdrive import list_files_in_folder
from data import internal

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("matplotlib.font_manager").setLevel(logging.WARNING)


def balance_at_month(date, items):
    totals = {"USD": 0.0, "PYG": 0.0}
    for k, v in items.items():
        for asset in v:
            income = asset.get_income(date)
            if income[0] != 0.0:
                totals[k] += income[0]

    return totals["USD"] + totals["PYG"] / internal.exchange_rate("USDPYG")


def calculate_balance(items) -> float:
    totals = {"USD": 0.0, "PYG": 0.0}
    for k, v in items.items():
        for asset in v:
            income = asset.get_liquid_balance()
            if income[0] != 0.0:
                totals[k] += income[0]
    return totals["USD"] + totals["PYG"] / internal.exchange_rate("USDPYG")

def cash_flow():
    logging.debug("Listing files in Google Drive folder:")
    files = list_files_in_folder()

    items = {"USD": [], "PYG": []}
    for file in files:
        fetched = fetch_if_not_cached(file)
        if isinstance(fetched, list):
            for sub_item in fetched:
                items[sub_item.currency].append(sub_item)
        else:
            items[fetched.currency].append(fetched)

    balance = calculate_balance(items)
    x = []
    y = []
    for v in range(24307, (2031 * 12)):
        year = v // 12
        month = v % 12 + 1
        today = datetime(year, month, 1)
        totals = balance_at_month(today, items)
        balance += totals
        y.append(balance)
        x.append(f"{year}-{month:02d}")
        logging.info(f"{year}-{month} {year-1984}: {totals:,.2f} {balance:,.2f} USD")


    min_value = min(y)
    min_index = y.index(min_value)
    logging.info(f"Minimum value: {min_value:,.2f} USD in {x[min_index]}")
    return x, y
