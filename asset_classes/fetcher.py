import logging
import os
import pickle
from typing import Sequence

from mflow_shared_rralcala.data.datasource import DataSource

from asset_classes import account, bond, cd, instrument, payable
from asset_classes import property as reprop
from asset_classes import recurrent
from asset_classes.asset import Asset


def fetch_if_not_cached(data_file: DataSource) -> Asset | Sequence[Asset]:
    """
    Fetches data from a sheet if not cached.
    """
    path = "./cache/" + data_file.name + ".pkl"
    if os.path.exists(path) and os.path.getmtime(path) >= data_file.mtime:
        logging.debug("Loading from cache: %s", path)
        with open(path, "rb") as f:
            item = pickle.load(f)
            if isinstance(item, instrument.Instrument):
                item.need_update = True
    else:
        logging.debug("%s not found or older, loading from Cloud", path)
        item = fetch_from_google(data_file)
        if data_file.source_type == "google":
            with open(path, "wb") as f:
                pickle.dump(item, f)
    logging.debug("Loaded: %s", item)
    return item


def fetch_from_google(sheet):
    data = sheet.get_sheet_settings()
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


def fetch_assets(files) -> dict[str, list[Asset]]:
    """Apply fetching logic and call fetch_if_not_cached for each asset file."""
    items = {"USD": [], "PYG": []}
    for file in files:

        if file.name == "Transactions-1":
            logging.debug("Skipping asset data for %s", file.name)
            continue
        logging.debug("Fetching asset data for <%s>", file.name)
        try:
            fetched = fetch_if_not_cached(file)
        except ValueError as e:
            logging.error(f"fetch_assets: In {file.name}: {e}")
            continue
        if isinstance(fetched, Sequence):
            for sub_item in fetched:
                items[sub_item.get_currency()].append(sub_item)
        else:
            items[fetched.get_currency()].append(fetched)
    return items
