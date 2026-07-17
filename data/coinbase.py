from datetime import datetime
from typing import Generator, List

from coinbase.rest import RESTClient
from requests.exceptions import HTTPError

from asset_classes.instrument import Instrument
from lib.logger import get_logger

Logger = get_logger()


def get_accounts(api_key: str, api_secret: str, portfolio_id: str) -> Generator:
    if api_key == "":
        raise ValueError("Coinbase API Key is not set.")
    client = RESTClient(api_key=api_key, api_secret=api_secret)
    try:
        portfolio = client.get_portfolio_breakdown(portfolio_id)
    except HTTPError as e:
        Logger.error(f"Error fetching portfolio breakdown: {e}")
        return
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


def fetch_cb_assets(key, secret, portfolio_id, stake_rates) -> List[Instrument]:
    assets = []
    for position in get_accounts(key, secret, portfolio_id):
        fiat_balance = float(position["total_balance_fiat"])
        if fiat_balance < 0.1:
            continue
        qty = float(position["total_balance_crypto"])
        rate = stake_rates.get(position["asset"], 0.0)
        account = Instrument(
            country="US",
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
            liquid=position["asset"] == "USDC",
            capital_rate=0.0,  # Calculate based on 10Y chg
        )
        assets.append(account)
    return assets
