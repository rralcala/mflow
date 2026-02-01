from coinbase.rest import RESTClient


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
