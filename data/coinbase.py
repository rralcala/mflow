from datetime import datetime
from typing import List

from coinbase.rest import RESTClient

from asset_classes.instrument import Instrument
from lib.config import Config

RATES = {
    "USDC": 0.035,
    "SOL": 0.0412,
    "ETH": 0.0,
}


def get_accounts(api_key: str, api_secret: str, portfolio_id: str):
    if api_key == "":
        raise ValueError("Coinbase API Key is not set.")
    client = RESTClient(api_key=api_key, api_secret=api_secret)

    portfolio = client.get_portfolio_breakdown(portfolio_id)
    # Get account balances
    spot_positions = portfolio.to_dict()["breakdown"]["spot_positions"]
    for position in spot_positions:
        yield position


def get_portfolios(api_key: str, api_secret: str):
    if api_key == "":
        raise ValueError("Coinbase API Key is not set.")
    client = RESTClient(api_key=api_key, api_secret=api_secret)

    portfolios = client.get_portfolios()
    return portfolios


def fetch_cb_assets() -> List[Instrument]:
    assets = []
    for position in get_accounts(
        Config.COINBASE_API_KEY,
        Config.COINBASE_API_SECRET,
        Config.COINBASE_PORTFOLIO_ID,
    ):
        fiat_balance = float(position["total_balance_fiat"])
        if fiat_balance < 0.1:
            continue
        qty = float(position["total_balance_crypto"])
        rate = RATES.get(position["asset"], 0.0)
        account = Instrument(
            location="Coinbase",
            symbol=position["asset"],
            price=fiat_balance / qty,
            factor=1.0,
            qty=qty,
            estimated_dividend=qty * rate / 12,
            rate=rate,
            dividend="0 0 1 * *",
            currency="USD",
            acquisition_date=datetime(2026, 2, 10),
            acquisition_price=float(position["average_entry_price"]["value"]),
            liquid=False,
        )
        assets.append(account)
    return assets
