import os
import sys
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(script_dir, '..')
sys.path.insert(0, project_root)

import datetime
import logging

import data.internal
from data.gdrive import list_files_in_folder


def get_items():
    files = list_files_in_folder()
    return data.internal.fetch_assets(files)

logging.debug("Listing files in Google Drive folder:")
asset_list = get_items()

per_cur = {"PYG": 0.0, "USD": 0.0}
curdate = datetime.datetime(year=2025, month=12, day=1, hour=0, minute=0, second=0)
for currency, assets in asset_list.items():
    for asset in assets:
        value, _ = asset.get_income(curdate)
        if value < 0.0:
            per_cur[currency] += value
            print(asset)
print(per_cur)