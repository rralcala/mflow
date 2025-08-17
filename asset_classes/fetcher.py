import logging
import pickle

from asset_classes.asset import Asset
from asset_classes import account, instrument, recurrent, property, payable
from asset_classes.bond import fetch_bond
from asset_classes.cd import fetch_cd
from lib.gdrive import get_sheet_settings

def fetch_if_not_cached(sheet: str) -> Asset:
    """
    Fetches data from a sheet if not cached.
    """
    path = "./cache/" + sheet + ".pkl"
    try:
        with open(path, "rb") as f:
            item = pickle.load(f)
    except FileNotFoundError:
        data = get_sheet_settings(sheet)
        itype = data.get("itype").lower()
        if itype == "cd":
            item = fetch_cd(sheet)
        elif itype == "cash":
            item = account.fetch_accounts(sheet, "Accounts")
        elif itype == "recurrent":
            item = recurrent.fetch_recurrent(sheet)
        elif itype == "property":
            item = property.fetch_properties(sheet)
        elif itype == "bond":
            item = fetch_bond(sheet)
        elif itype == "portfolio":
            item = instrument.fetch_portfolio(sheet)
        elif itype == "payable":
            item = payable.fetch_payables(sheet)
        else:
            raise ValueError(f"Unknown type: {itype}")
        with open(path, "wb") as f:
            pickle.dump(item, f)
    logging.info(f"Loaded: {item}")
    return item