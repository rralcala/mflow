from pathlib import Path
from typing import Callable, Dict, List

from data import gdrive, xl


def load_assets(
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
