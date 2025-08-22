from datetime import datetime
from typing import Sequence
import argparse
import csv
import logging
import matplotlib.pyplot as plt
import sys

from asset_classes.fetcher import fetch_if_not_cached
from lib.config import USDPYG
from lib.gdrive import list_files_in_folder


def check_history(tpval: float, tnval: float):
    ordered_history = []
    with open("history.csv", "r", encoding="utf-8") as csvfile:
        # Create a reader object
        csv_reader = csv.reader(csvfile)
        today = datetime.now()
        # Iterate through each row in the CSV file
        for row in csv_reader:
            ordered_history.append([row[0], float(row[1].replace(",", ""))])

    new_key = f"{today.month}-{today.year}"
    if ordered_history[-1][0] == new_key:
        ordered_history[-1][1] = tpval + tnval
    else:
        ordered_history.append([new_key, tpval + tnval])

    with open("history.csv", "w", encoding="utf-8") as file:
        writer = csv.writer(file)
        for _, row in enumerate(ordered_history):
            data = [row[0], f"{row[1]:,.2f}"]
            logging.debug("Writing to history: %s", data)
            writer.writerow(data)
    p = ordered_history[-6][1]
    x = []
    y = []
    for i in range(-6, 0):
        v = ordered_history[i][1]
        logging.info(f"{ordered_history[i][0]}: {v:,.2f} {(v-p):,.2f} USD")

        y.append(v - p)
        x.append(ordered_history[i][0])
        p = v

    plt.plot(x, y)
    plt.xticks(rotation=90)
    plt.hlines(y=0, xmin=x[0], xmax=x[-1], colors="red", linestyles="dashed")
    plt.xlabel("Month")
    plt.ylabel("Dollar Savings")
    plt.title(f"Asset Value Change History {(tpval + tnval):,.0f}")
    plt.show()


parser = argparse.ArgumentParser(description="Calculate cash flow.")
parser.add_argument("-p", "--print-pos", action="store_true", help="Create chart.")
parser.add_argument("-d", "--debug", action="store_true", help="Create chart.")
parser.add_argument("-n", "--print-neg", action="store_true", help="Create chart.")
parser.add_argument("-c", "--check-history", action="store_true", help="Create chart.")
args = parser.parse_args()

if args.debug:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)


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


logging.getLogger("urllib3").setLevel(logging.WARNING)

logging.debug("Listing files in Google Drive folder:")

files = list_files_in_folder()
if not files:
    logging.error("No files found in the specified Google Drive folder.")
    sys.exit(1)

items = fetch_assets(files)

logging.debug("Fetched %i assets:", len(items))
tpval = 0.0
tnval = 0.0
returns = []
for k, sub in items.items():
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
            returns.append([current_value / USDPYG, current_return, asset.identifier])
        else:
            returns.append([current_value, current_return, asset.identifier])

        if current_value > 0:
            if args.print_pos:
                logging.info(
                    "Positive asset found: %s with value %s %s",
                    asset.identifier,
                    f"{current_value:,.0f}",
                    currency,
                )
            pval += current_value
        elif current_value < 0:
            if args.print_neg:
                logging.info(
                    f"Negative asset found: {asset.identifier} with value {current_value:,.0f} {currency}"
                )
            nval += current_value

    if k == "PYG":
        pval /= USDPYG
        nval /= USDPYG
    tpval += pval
    tnval += nval
    if not args.check_history:
        logging.info(
            f"Positive value: {pval:,.2f}USD in {k}, Negative value: {nval:,.2f}USD in {k}"
        )

if not args.check_history:
    ret = 0.0
    grand_total = tpval + tnval
    for current_value, current_return, asset_id in returns:
        tret = (current_value / grand_total) * current_return
        ret += tret
    logging.info(
        f"Total positive value: {tpval:,.2f} USD, Total negative value: {tnval:,.2f} USD"
    )
    logging.info(f"Total portfolio value: {grand_total:,.2f} USD {ret*100:,.2f}% annualized return")

else:
    logging.info("Generating History")
    check_history(tpval, tnval)
