from datetime import datetime
from typing import List

from coinbase.rest import RESTClient

from asset_classes.instrument import Instrument
from lib.config import Config

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
        if position["asset"] == "USDC":
            qty = float(position["total_balance_crypto"])
            rate = 0.045
            account = Instrument(
                location="Coinbase",
                symbol="USDC",
                price=1.0,
                factor=1.0,
                qty=qty,
                estimated_dividend=qty * rate / 12,
                rate=rate,
                dividend="0 0 1 * *",
                currency="USD",
                acquisition_date=datetime(2025, 9, 24),
                acquisition_price=1.0,
                liquid=True,
            )
            assets.append(account)
        if position["asset"] == "SOL":
            qty = float(position["total_balance_crypto"])
            rate = 0.0424
            account = Instrument(
                location="Coinbase",
                symbol="SOLUSD",
                price=float(position["total_balance_fiat"]) / qty,
                factor=1.0,
                qty=qty,
                estimated_dividend=qty * rate / 12,
                rate=rate,
                dividend="0 0 1 * *",
                currency="USD",
                acquisition_date=datetime(2025, 9, 24),
                acquisition_price=float(position["cost_basis"]["value"]) / qty,
                liquid=False,
            )
            assets.append(account)

        if position["asset"] == "ETH":
            qty = float(position["total_balance_crypto"])
            rate = 0.0
            account = Instrument(
                location="Coinbase",
                symbol="ETHUSD",
                price=float(position["total_balance_fiat"]) / qty,
                factor=1.0,
                qty=qty,
                estimated_dividend=qty * rate / 12,
                rate=rate,
                dividend="0 0 1 * *",
                currency="USD",
                acquisition_date=datetime(2026, 2, 10),
                acquisition_price=float(position["cost_basis"]["value"]) / qty,
                liquid=False,
            )
            assets.append(account)
    return assets