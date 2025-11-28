from datetime import datetime

from coinbase.rest import RESTClient

from asset_classes.instrument import Instrument
from lib.config import COINBASE_API_KEY, COINBASE_API_SECRET, COINBASE_PORTFOLIO_ID


def get_usdc_account():
    # Replace with your own API Keys and ensure you use the correct key format (organizations/{org_id}/apiKeys/{key_id})
    client = RESTClient(api_key=COINBASE_API_KEY, api_secret=COINBASE_API_SECRET)

    accounts = client.get_portfolio_breakdown(COINBASE_PORTFOLIO_ID)
    # Get account balances
    spot_positions = accounts.to_dict()["breakdown"]["spot_positions"]
    for position in spot_positions:
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
            return account
    return None
