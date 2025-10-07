from asset_classes.fetcher import fetch_assets
from data.gdrive import list_files_in_folder


def load_assets():
    assets = {}
    files = list_files_in_folder()
    if not files:
        raise FileNotFoundError("No files found in the specified Google Drive folder.")

    assets = fetch_assets(files)
    return assets
