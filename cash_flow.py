import argparse
import logging
from datetime import datetime

import matplotlib.pyplot as plt

from asset_classes.fetcher import fetch_if_not_cached
from lib.config import USDPYG
from lib.gdrive import list_files_in_folder

TODAY = datetime.strptime("09/01/2025", "%m/%d/%Y")
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

    return totals["USD"] + totals["PYG"] / USDPYG


def calculate_balance(items) -> float:
    totals = {"USD": 0.0, "PYG": 0.0}
    for k, v in items.items():
        for asset in v:
            income = asset.get_liquid_balance()
            if income[0] != 0.0:
                totals[k] += income[0]
    return totals["USD"] + totals["PYG"] / USDPYG


parser = argparse.ArgumentParser(description="Calculate cash flow.")
parser.add_argument("-p", "--plot", action="store_true", help="Create chart.")
args = parser.parse_args()

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
AGE_57 = (1984 + 57) * 12 + 8
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

if args.plot:
    logging.info("Plotting enabled.")
    plt.plot(x, y)
    plt.xticks(rotation=90)
    plt.hlines(y=0, xmin=x[0], xmax=x[-1], colors="red", linestyles="dashed")
    plt.xlabel("Month")
    plt.ylabel("Dollar Balance")
    plt.title("Cash Flow Over Time")
    plt.show()
