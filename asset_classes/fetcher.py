from typing import Sequence
import logging
import os
import pickle

from asset_classes import account, bond, cd, instrument, payable
from asset_classes import property as reprop
from asset_classes import recurrent
from asset_classes.asset import Asset
from data.gdrive import get_sheet_settings


def fetch_if_not_cached(sheet: str) -> Asset | Sequence[Asset]:
    """
    Fetches data from a sheet if not cached.
    """
    path = "./cache/" + sheet + ".pkl"
    if os.path.exists(path):
        with open(path, "rb") as f:
            item = pickle.load(f)
            if isinstance(item, instrument.Instrument):
                item.need_update = True
    else:
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
        with open(path, "wb") as f:
            pickle.dump(item, f)
    logging.debug("Loaded: %s", item)
    return item
