import logging
from typing import List
from asset_classes.fetcher import fetch_if_not_cached
from lib import util

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.WARNING)

USDPYG = util.USDPYG


flow = {"USD": 0.0, "PYG": 0.0}

bond = fetch_if_not_cached("BOND-Tapepora-1")

bond = fetch_if_not_cached("BOND-Telecel-1")
logging.debug(bond.get_income())

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
