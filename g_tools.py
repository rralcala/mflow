from gspread import service_account

USDPYG = 7500

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
