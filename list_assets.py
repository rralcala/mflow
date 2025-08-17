import logging
import pprint
from typing import List

from asset_classes.fetcher import fetch_if_not_cached
from asset_classes import account
from lib import util
from lib.gdrive import list_files_in_folder


USDPYG = util.USDPYG

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.WARNING)

logging.debug("Listing files in Google Drive folder:")

files = list_files_in_folder()
items = { "USD": [], "PYG": [] }
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
for k,v in items.items():
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
    logging.info(f"Positive value: {pval:,.2f}USD in {k}, Negative value: {nval:,.2f}USD in {k}")
logging.info(f"Total positive value: {tpval:,.2f} USD, Total negative value: {tnval:,.2f} USD")
logging.info(f"Total portfolio value: {tpval + tnval:,.2f} USD")




"""
total_balance = 0.0
flow = {"USD": 0.0, "PYG": 0.0}

bond = fetch_if_not_cached("BOND-Tapepora-1")
total_balance += bond.capital / USDPYG if bond.currency == "PYG" else bond.capital
#logging.debug(f"{bond.bond_id}: {bond.capital if bond.currency == 'USD' else bond.capital / USDPYG}")
bond = fetch_if_not_cached("BOND-Telecel-1")
logging.debug(bond.get_income())

cd = fetch_if_not_cached("CD-PY-SUD-1777943")
total_balance += cd.get_total_value(USDPYG)

cd = fetch_if_not_cached("CD-PY-UENO-1")
total_balance += cd.get_total_value(USDPYG)

cd = fetch_if_not_cached("CD-PY-CONT-1")
total_balance += cd.get_total_value(USDPYG)

accounts = fetch_if_not_cached("CASH")
total_balance += account.get_total_value(accounts, USDPYG)

loan = fetch_if_not_cached("REC-Tania-1")
amount, currency = loan.get_income()
flow[currency] += amount

loan = fetch_if_not_cached("LOAN-Domi-1")
amount, currency = loan.get_income()
flow[currency] += amount

mirador = fetch_if_not_cached("REC-Mirador")
amount, currency = mirador.get_income()
flow[currency] += amount


properties = fetch_if_not_cached("PROP-1")
for prop in properties:
    amount, currency = prop.get_income()
    flow[currency] += amount


assets = fetch_if_not_cached("PORTFOLIO-1")
for asset in assets:
    amount, currency = asset.get_income()
    flow[currency] += amount

print(f"{flow} {flow['USD'] + flow['PYG']/USDPYG:,.2f}")
print(f"{total_balance:,.2f}")
"""