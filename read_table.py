import logging
logging.getLogger("urllib3").setLevel(logging.WARNING)

import pickle
from typing import List

from asset_classes import portfolio
from asset_classes import account
from asset_classes.bond import fetch_bond
from asset_classes import property
from asset_classes import recurrent
from asset_classes.cd import fetch_cd
from g_tools import get_sheet_settings

logging.basicConfig(level=logging.DEBUG)
USDPYG = 7500

def print_table(data: List[List[str]]):
    """
    Function to print the data in a formatted way.

    :param data: List of lists containing the data to be printed.
    """
    for row in data:
        print("\t".join(row))

def fetch_if_not_cached(sheet: str):
    """
    Fetches data from a sheet if not cached.
    """
    path = "./cache/" + sheet + ".pkl"
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        data = get_sheet_settings(sheet)
        itype = data.get("itype")
        if itype == "CD":
            instrument = fetch_cd(sheet)
        elif itype == "Cash":
            instrument = account.fetch_accounts(sheet, "Accounts")
        elif itype == "recurrent":
            instrument = recurrent.fetch_recurrent(sheet)
        elif itype == "property":
            instrument = property.fetch_properties(sheet)
        elif itype == "bond":
            instrument = fetch_bond(sheet)
        elif itype == "portfolio":
            instrument = portfolio.fetch_portfolio(sheet)
        else:
            raise ValueError(f"Unknown type: {itype}")
        with open(path, "wb") as f:
            pickle.dump(instrument, f)
        return instrument
total_balance = 0.0
flow = {"USD": 0.0, "PYG": 0.0}

bond = fetch_if_not_cached("BOND-Tapepora-1")
total_balance += bond.capital / USDPYG if bond.currency == "PYG" else bond.capital
#logging.debug(f"{bond.bond_id}: {bond.capital if bond.currency == 'USD' else bond.capital / USDPYG}")
bond = fetch_if_not_cached("BOND-Telecel-1")
total_balance += bond.capital / USDPYG if bond.currency == "PYG" else bond.capital
#logging.debug(f"{bond.bond_id}: {bond.capital if bond.currency == 'USD' else bond.capital / USDPYG}")
cd = fetch_if_not_cached("CD-PY-SUD-1777943")
total_balance += cd.get_total_value()

cd = fetch_if_not_cached("CD-PY-UENO-1")
total_balance += cd.get_total_value()

cd = fetch_if_not_cached("CD-PY-CONT-1")
total_balance += cd.get_total_value()

accounts = fetch_if_not_cached("CASH")
total_balance += account.get_total_value(accounts)

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
print(f"{total_balance-2200000.0:,.2f}")
