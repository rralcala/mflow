import logging
from typing import List
from asset_classes.fetcher import fetch_if_not_cached
from asset_classes import account
from lib import util

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.WARNING)

USDPYG = util.USDPYG

def print_table(data: List[List[str]]):
    """
    Function to print the data in a formatted way.

    :param data: List of lists containing the data to be printed.
    """
    for row in data:
        print("\t".join(row))

total_balance = 0.0
flow = {"USD": 0.0, "PYG": 0.0}

bond = fetch_if_not_cached("BOND-Tapepora-1")
total_balance += bond.capital / USDPYG if bond.currency == "PYG" else bond.capital
#logging.debug(f"{bond.bond_id}: {bond.capital if bond.currency == 'USD' else bond.capital / USDPYG}")
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
print(f"{total_balance:,.2f}")
