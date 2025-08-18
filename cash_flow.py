import logging
from datetime import datetime

from asset_classes.fetcher import fetch_if_not_cached
from lib.gdrive import list_files_in_folder
from lib.config import USDPYG

TODAY = datetime.strptime("09/01/2025", "%m/%d/%Y")
logging.basicConfig(level=logging.DEBUG)
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

logging.info(f"Fetched {len(items)} assets:")

totals = {"USD": 0.0, "PYG": 0.0}
for k, v in items.items():
    logging.info(f"{k}: {len(v)} assets")
    for asset in v:
        income = asset.get_income(TODAY)
        if income[0] != 0.0:
            logging.info(f"{income[0]:,.2f} {income[1]} from {asset.identifier}")
            totals[k] += income[0]
logging.info(f"Total income in USD: {totals['USD']:,.2f} USD")
logging.info(f"Total income in PYG: {totals['PYG']:,.2f} PYG")
logging.info(f"Total income: {totals['USD'] + totals['PYG'] / USDPYG:,.2f}")
logging.info("---###END###---")
for k, v in items.items():
    logging.info(f"{k}: {len(v)} assets")
    for asset in v:
        income = asset.get_liquid_balance()
        if income[0] != 0.0:
            logging.info(f"{income[0]:,.2f} {income[1]} from {asset.identifier}")
            totals[k] += income[0]

logging.info(f"Total EOM in USD: {totals['USD']:,.2f} USD")
logging.info(f"Total EOM in PYG: {totals['PYG']:,.2f} PYG")
logging.info(f"Total EOM: {totals['USD'] + totals['PYG'] / USDPYG:,.2f}")
