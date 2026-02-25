import json

from coinbase.rest import RESTClient

import data.coinbase
from lib.config import Config
from lib.util import PRINTER

if __name__ == "__main__":
    try:
        with open("/config.json", "r") as f:
            config_data = json.load(f)

            for key, value in config_data.items():
                setattr(Config, key, value)
    except json.JSONDecodeError:
        print(f"Error:  is not a valid JSON file.")
    portfolios = data.coinbase.get_portfolios(
        Config.COINBASE_API_KEY, Config.COINBASE_API_SECRET
    )["portfolios"]
    print(PRINTER.pformat(portfolios))
    for portfolio in portfolios:
        print(f"Portfolio: {portfolio['name']} (ID: {portfolio['uuid']})")
        client = RESTClient(
            api_key=Config.COINBASE_API_KEY, api_secret=Config.COINBASE_API_SECRET
        )

        portfolio_d = client.get_portfolio_breakdown(portfolio["uuid"])
        print(json.dumps(portfolio_d.to_dict()))
