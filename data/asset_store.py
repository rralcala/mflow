from typing import Callable, Dict, List

from asset_classes.fetcher import fetch_assets
from asset_classes import recurrent
from data import gdrive, xl
from data.coinbase import fetch_cb_assets
from lib.config import Config

def load_sheet_assets(
    fetch_assets: Callable[[List], Dict[str, List]],
    xl_base_path: str,
    service_account_file: str,
) -> Dict[str, List]:
    gdrive.load_credentials(xl_base_path + service_account_file)
    files = gdrive.discover_assets()
    xl.set_base_path(xl_base_path)
    files = xl.discover_assets() + files
    if files:
        assets = fetch_assets(files)
    else:
        assets = {"USD": [], "PYG": []}

    return assets

def load_assets(recurrent_model) -> Dict[str, List]:
    assets = load_sheet_assets(fetch_assets, Config.BASE_PATH, "gdrive_key.json")
    assets['USD'] += fetch_cb_assets()

    for row in recurrent_model.query.all():
        asset = recurrent.Recurrent(
            identifier=str(row.identifier),
            parent_asset_id=str(row.parent_asset_id),
            country=row.country,
            amount=float(row.amount),
            currency=str(row.currency),
            recurrence=row.recurrence,
            start=row.start,
            end=row.end,
            flow_class=row.flow_class,
            rate=float(row.rate),
        )
        assets[asset.currency].append(asset)
    return assets