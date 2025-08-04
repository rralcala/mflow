from typing import List, Tuple

from g_tools import get_table, USDPYG


class Asset:
    """Represents a financial asset with its attributes and methods to calculate its value."""

    qty: float
    price: float
    currency: str
    location: str
    symbol: str
    factor: float

    def __init__(
        self,
        location: str,
        symbol: str,
        price: float,
        factor: float,
        qty: float,
    ):
        self.symbol = symbol
        self.price = price
        self.factor = factor
        self.qty = qty
        self.currency = "USD"
        self.location = location

    def get_usd_value(self):
        """
        Returns the value of the asset in USD.
        """
        return self.qty * self.price * self.factor

    def __repr__(self):
        return f"Asset(symbol={self.symbol}, value={self.get_usd_value()}, currency={self.currency}, location={self.location})"


def fetch_portfolio(sheet: str, worksheet: str) -> Tuple[List[Asset], float]:
    data = get_table(sheet, "Summary")

    if data[0][0] != "Type" or data[0][1] != "Portfolio":
        raise ValueError("The first cell of the Summary sheet must be 'Type' and the")

    ac_data = get_table(sheet, worksheet)
    assets: List[Asset] = parse_portfolio(ac_data)
    sum_balance: float = 0.0
    for account in assets:
        if account.currency == "PYG":
            sum_balance += account.qty * account.price * account.factor / USDPYG
        else:
            sum_balance += account.qty * account.price * account.factor
    return assets, sum_balance


def parse_portfolio(data: List[List[str]]) -> List[Asset]:
    """
    Function to parse account data from the provided data.

    :param data: List of lists containing the account data.
    :return: List of dictionaries with account information.
    """
    parsed_accounts: List[Asset] = []
    for row in data[1:]:  # Skip header row
        asset = Asset(
            location=row[0],
            symbol=row[1],
            price=float(row[2].replace(",", "")),
            factor=float(row[3].replace(",", "")),
            qty=float(row[4].replace(",", "")),
            )
        if len(row) < 5:
            continue  # Skip rows that do not have enough columns
        parsed_accounts.append(asset)

    return parsed_accounts