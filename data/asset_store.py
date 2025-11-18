from typing import Dict, List

from asset_classes.fetcher import fetch_assets
import data.gdrive

def load_assets() -> Dict[str, List]:
    files = data.gdrive.discover_assets()
    if not files:
        return {}
    assets = fetch_assets(files)
    return assets
