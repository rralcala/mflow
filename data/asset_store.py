import logging
from typing import Dict, List

import data.coinbase
import data.gdrive
import data.xl
from asset_classes.fetcher import fetch_assets

ASSET_CACHE = None


def load_assets() -> Dict[str, List]:
    global ASSET_CACHE
    if ASSET_CACHE is not None:
        return ASSET_CACHE
    logging.info("Loading assets...")
    files = data.gdrive.discover_assets()
    files = data.xl.discover_assets() + files
    if files:
        assets = fetch_assets(files)
    else:
        assets = {"USD": [], "PYG": []}
    assets["USD"] = assets["USD"] + data.coinbase.get_usdc_account()
    ASSET_CACHE = assets
    return ASSET_CACHE
