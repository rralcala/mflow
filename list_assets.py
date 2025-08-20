import logging
import argparse
from asset_classes.fetcher import fetch_if_not_cached
from lib.config import USDPYG
from lib.gdrive import list_files_in_folder
import csv
import matplotlib.pyplot as plt


parser = argparse.ArgumentParser(description="Calculate cash flow.")
parser.add_argument("-p", "--print-pos", action="store_true", help="Create chart.")
parser.add_argument("-d", "--debug", action="store_true", help="Create chart.")
parser.add_argument("-n", "--print-neg", action="store_true", help="Create chart.")
parser.add_argument("-c", "--check-history", action="store_true", help="Create chart.")
args = parser.parse_args()

if args.debug:
    level=logging.DEBUG
else:
    level=logging.INFO
logging.basicConfig(level=level)
logging.getLogger("urllib3").setLevel(logging.WARNING)

logging.debug("Listing files in Google Drive folder:")

files = list_files_in_folder()

items = {"USD": [], "PYG": []}
for file in files:
    logging.debug(f"Fetching asset data for {file}")
    fetched = fetch_if_not_cached(file)
    if isinstance(fetched, list):
        for sub_item in fetched:
            items[sub_item.currency].append(sub_item)
    else:
        items[fetched.currency].append(fetched)

logging.debug(f"Fetched {len(items)} assets:")
tpval = 0.0
tnval = 0.0
for k, v in items.items():
    print(f"{k}: {len(v)} assets")
    pval = 0.0
    nval = 0.0
    for asset in v:
        curval, currency = asset.get_current_value()
        if curval > 0:
            if args.print_pos:
                logging.info(f"Positive asset found: {asset.identifier} with value {curval:,.0f} {currency}")
            pval += curval
        elif curval < 0:
            if args.print_neg:
                logging.info(f"Negative asset found: {asset.identifier} with value {curval:,.0f} {currency}")
            nval += curval

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
    logging.info(
        f"Total positive value: {tpval:,.2f} USD, Total negative value: {tnval:,.2f} USD"
    )
    logging.info(f"Total portfolio value: {tpval + tnval:,.2f} USD")
else:
    logging.info(f"History")
    history = {}
    with open('history.csv', 'r') as csvfile:
        # Create a reader object
        csv_reader = csv.reader(csvfile)

    
        # Iterate through each row in the CSV file
        for row in csv_reader:
            history[row[0]] = float(row[1].replace(',', ''))
        history["8-2025"] = tpval + tnval
        #print(history)
        start_y = 2025
        start_m = 5
        p = history.get(f"{start_m}-{start_y}", 0.0)
        x = []
        y = []
        for m in range(start_m, 9):
            key = f"{m}-{start_y}"
            v = history.get(key, 0.0)
            logging.info(f"{key}: {v:,.2f} {(v-p):,.2f} USD")
            
            y.append(v-p)
            x.append(key)
            p = v
        plt.plot(x, y)
        plt.xticks(rotation=90)
        plt.hlines(y=0, xmin=x[0], xmax=x[-1], colors='red', linestyles='dashed')
        plt.xlabel('Month')
        plt.ylabel('Dollar Savings')
        plt.title(f"Asset Value Change History {(tpval + tnval):,.0f}")
        plt.show()