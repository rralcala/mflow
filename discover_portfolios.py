import json

import data.coinbase
from lib.config import Config

if __name__ == "__main__":
    with open(Config.BASE_PATH + "cdp_api_key.json", "r") as file:
        content = json.loads(file.read())
        API_KEY = content.get("name", "")
        API_SECRET = content.get("privateKey", "")

    print(data.coinbase.get_portfolios(API_KEY, API_SECRET))
