import logging

from asset_classes.fetcher import fetch_if_not_cached
from asset_classes import account
from lib.config import USDPYG
from lib.gdrive import list_files_in_folder


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
tpval = 0.0
tnval = 0.0
for k, v in items.items():
    print(f"{k}: {len(v)} assets")
    pval = 0.0
    nval = 0.0
    for asset in v:
        curval = asset.get_current_value()[0]
        if curval > 0:
            pval += curval
        else:
            nval += curval

    if k == "PYG":
        pval /= USDPYG
        nval /= USDPYG
    tpval += pval
    tnval += nval
    logging.info(
        f"Positive value: {pval:,.2f}USD in {k}, Negative value: {nval:,.2f}USD in {k}"
    )
logging.info(
    f"Total positive value: {tpval:,.2f} USD, Total negative value: {tnval:,.2f} USD"
)
logging.info(f"Total portfolio value: {tpval + tnval:,.2f} USD")
