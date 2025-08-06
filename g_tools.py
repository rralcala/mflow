from typing import List, Dict, Any

from gspread import service_account

USDPYG = 7500

# Authenticate with your service account credentials
# Replace 'path/to/your/service_account.json' with the actual path
client = service_account(filename="./key.json")

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

def get_sheet_settings(sheet: str) -> Dict[str, Any]:
    """
    Function to retrieve settings from a specific sheet.
    :param sheet: The title of the Google Sheet.
    :return: Dictionary containing the settings from the "Summary" worksheet.
    """
    settings = get_dict(sheet, "Summary")
    return settings
