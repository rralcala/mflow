import data.coinbase
from lib import config
import json

with open(config.BASE_PATH + "cdp_api_key.json", "r") as file:
    content = json.loads(file.read())
    API_KEY = content.get("name", "")
    API_SECRET = content.get("privateKey", "")
    #config.COINBASE_PORTFOLIO_ID = content.get("portfolioId", "") 
print(data.coinbase.get_portfolios(API_KEY, API_SECRET))