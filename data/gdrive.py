from datetime import datetime
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from google.oauth2 import service_account
from googleapiclient.discovery import build
from gspread import service_account as gspread_service_account
from gspread.exceptions import APIError

from data.datasource import DataSource

SERVICE_ACCOUNT_FILE = Path("./key.json")
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# Replace with your folder ID
FOLDER_ID = "1gIMkSpMDygnUH1C13hKHZi1VVF8FUzk5"

# Authenticate with your service account credentials
# Replace 'path/to/your/service_account.json' with the actual path
# Path to your service account key file
client = gspread_service_account(SERVICE_ACCOUNT_FILE.absolute())


def retry(times, exceptions):
    """
    Retry Decorator
    Retries the wrapped function/method `times` times if the exceptions listed
    in ``exceptions`` are thrown
    :param times: The number of times to repeat the wrapped function/method
    :type times: Int
    :param Exceptions: Lists of exceptions that trigger a retry attempt
    :type Exceptions: Tuple of Exceptions
    """

    def decorator(func):
        def newfn(*args, **kwargs):
            attempt = 0
            while attempt < times:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    logging.error(
                        "Exception thrown when attempting to run %s, attempt %d of %d",
                        func,
                        attempt,
                        times,
                    )
                    logging.error(e)
                    time.sleep(60)  # Exponential backoff
                    attempt += 1
            return func(*args, **kwargs)

        return newfn

    return decorator


@retry(3, (APIError,))
def get_table(sheet: str, worksheet: str):
    """
    Function to retrieve data from a Google Sheet.

    :param sheet: The title of the Google Sheet.
    :param worksheet: The name of the worksheet within the sheet.
    :return: List of lists containing the data from the specified worksheet.
    """
    # Open the Google Sheet by its title
    spreadsheet = client.open(sheet)

    # Select the desired worksheet
    ws = spreadsheet.worksheet(worksheet)

    # Get all values from the worksheet
    return ws.get_all_values()


def get_dict(sheet: str, worksheet: str) -> Dict[str, Any]:
    table: List[List[Any]] = get_table(sheet, worksheet)
    result = {}

    for row in table:
        if len(row) < 2:
            continue

        result[row[0].lower()] = row[1]
    return result


@retry(3, (APIError,))
def get_sheet_settings(sheet: str) -> Dict[str, Any]:
    """
    Function to retrieve settings from a specific sheet.
    :param sheet: The title of the Google Sheet.
    :return: Dictionary containing the settings from the "Summary" worksheet.
    """
    settings = get_dict(sheet, "Summary")
    return settings


def discover_assets() -> List[DataSource]:
    """
    Lists all files in a specific Google Drive folder."""
    # Authenticate and build the service
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    service = build("drive", "v3", credentials=creds)

    # Query for files in the folder
    results = (
        service.files()
        .list(
            q=f"'{FOLDER_ID}' in parents and trashed=false",
            fields="files(id, name, modifiedTime, mimeType)",
        )
        .execute()
    )

    files = results.get("files", [])
    selected = []
    for file in filter(
        lambda f: f["mimeType"] == "application/vnd.google-apps.spreadsheet", files
    ):
        new_ds = DataSource(
            "google", file["name"], datetime.fromisoformat(file["modifiedTime"])
        )
        new_ds._get_table = get_table
        new_ds._get_dict = get_dict
        new_ds._get_sheet_settings = get_sheet_settings
        selected.append(new_ds)

    return selected
