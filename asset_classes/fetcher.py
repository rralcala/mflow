import logging
import os
import pickle
from typing import Dict, Sequence

from asset_classes import account, bond, cd, instrument, payable
from asset_classes import property as reprop
from asset_classes import recurrent
from asset_classes.asset import Asset
from data.datasource import DataSource
from lib.config import Config


def fetch_if_not_cached(data_file: DataSource) -> Asset | Sequence[Asset]:
    """
    Fetches data from a sheet if not cached.
    """
    path = Config.SCRIPT_DIR / "cache" / (data_file.name + ".pkl")
    if data_file.source_type == "google":
        if os.path.exists(path) and os.path.getmtime(path) >= data_file.mtime:
            logging.info("Loading from cache: %s", path)
            with open(path, "rb") as f:
                item = pickle.load(f)
                return item
        else:
            logging.info("%s not found or older, loading from source", path)

    item = fetch_from_spreadsheet(data_file)
    if data_file.source_type == "google":
        with open(path, "wb") as f:
            pickle.dump(item, f)
    return item


def fetch_from_spreadsheet(sheet):
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


def fetch_assets(files, items: Dict) -> Dict[str, list[Asset]]:
    """Apply fetching logic and call fetch_if_not_cached for each asset file."""

    for file in files:
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
