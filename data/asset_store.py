from typing import Dict, List

from asset_classes.fetcher import fetch_assets
import data.gdrive
import data.xl
import data.coinbase


def load_assets() -> Dict[str, List]:
    files = data.gdrive.discover_assets()
    files = data.xl.discover_assets() + files
    if files:
        assets = fetch_assets(files)
    else:
        assets = {"USD": [], "PYG": []}
    assets["USD"] = assets["USD"] + data.coinbase.get_usdc_account()
    return assets
