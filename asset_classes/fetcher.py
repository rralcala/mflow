import logging
import os
import pickle
from datetime import datetime
from typing import Dict, Sequence

from asset_classes import account, bond, cd, instrument, payable
from asset_classes import property as reprop
from asset_classes import recurrent
from asset_classes.asset import Asset
from data.gdrive import get_sheet_settings


def fetch_if_not_cached(sheet: Dict) -> Asset | Sequence[Asset]:
    """
    Fetches data from a sheet if not cached.
    """
    path = "./cache/" + sheet[0] + ".pkl"
    cloud_mtime = datetime.fromisoformat(sheet[1])
    if os.path.exists(path) and os.path.getmtime(path) >= cloud_mtime.timestamp():
        logging.debug("Loading from cache: %s", path)
        with open(path, "rb") as f:
            item = pickle.load(f)
            if isinstance(item, instrument.Instrument):
                item.need_update = True
    else:
        logging.debug("%s not found or older, loading from Cloud", path)
        item = fetch_from_google(sheet[0])
        with open(path, "wb") as f:
            pickle.dump(item, f)
    logging.debug("Loaded: %s", item)
    return item


def fetch_from_google(sheet):
    data = get_sheet_settings(sheet)
    itype = data.get("itype", "").lower()
    if itype == "cd":
        item = cd.fetch(sheet)
    elif itype == "cash":
        item = account.fetch(sheet, "Accounts")
    elif itype == "recurrent":
        item = recurrent.fetch(sheet)
    elif itype == "property":
        item = reprop.fetch(sheet)
    elif itype == "bond":
        item = bond.fetch(sheet)
    elif itype == "portfolio":
        item = instrument.fetch(sheet)
    elif itype == "payable":
        item = payable.fetch(sheet)
    else:
        raise ValueError(f"Unknown type: {itype}")

    return item


def fetch_assets(files):
    """Apply fetching logic and call fetch_if_not_cached for each asset file."""
    items = {"USD": [], "PYG": []}
    for file in files:

        if file[0] == "Transactions-1":
            logging.debug("Skipping asset data for %s", file[0])
            continue
        logging.debug("Fetching asset data for <%s>", file[0])
        try:
            fetched = fetch_if_not_cached(file)
        except ValueError as e:
            logging.error(e)
            continue
        if isinstance(fetched, Sequence):
            for sub_item in fetched:
                items[sub_item.get_currency()].append(sub_item)
        else:
            items[fetched.get_currency()].append(fetched)
    return items
