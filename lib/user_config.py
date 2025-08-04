from threading import Lock
from typing import Dict, List

from asset_classes.asset import Asset
from lib.config import Config, load_config


class UserConfig:
    def __init__(self, user_id: str):
        self.USER_ID = user_id
        self.SECONDARY_CURRENCY = ""
        self.TRADED_STOCKS = []
        self.TRADED_CRYPTO = []
        self.LAST_UNTIL = "2075-01-01"
        self.DESIRED_ESTATE = 0.0
        self.DEFAULT_VAR_ID = "default_var"
        self.COINBASE_API_KEY = ""
        self.COINBASE_API_SECRET = ""
        self.COINBASE_PORTFOLIO_ID = ""
        self.CRYPTO_RATES: Dict  # Staking { "USDC": "0.035" }
        self.GDRIVE_FOLDER_ID = ""
        self.ASSETS: Dict[str, List[Asset]] = {}
        self.ASSET_STORE_LOCK = Lock()
        self.ASSET_STORE_UPDATE_TIME = None


class UserStore:
    user_config = {}

    @staticmethod
    def get_user_config(id: str) -> UserConfig:
        if id not in UserStore.user_config:
            UserStore.user_config[id] = UserConfig(id)
            load_config(
                Config.BASE_PATH / f"user-{id}" / "config.json",
                UserStore.user_config[id],
            )
        return UserStore.user_config[id]
