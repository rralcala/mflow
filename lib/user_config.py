from typing import Dict, List

from asset_classes.asset import Asset
from lib.config import Config, load_config


class UserConfig:
    def __init__(self, user_id: str):
        self.USER_ID = user_id
        self.SECONDARY_CURRENCY = ""
        self.SECONDARY_COUNTRY = "PY"
        self.LAST_UNTIL = "2075-01-01"
        self.DESIRED_ESTATE = 0.0
        # Yearly inflation per country, used by the future timeline projection.
        self.INFLATION_RATES: Dict[str, float] = {"US": 0.025, "UY": 0.025, "PY": 0.035}
        self.DEFAULT_VAR_ID = "default_var"
        self.COINBASE_API_KEY = ""
        self.COINBASE_API_SECRET = ""
        self.COINBASE_PORTFOLIO_ID = ""
        self.CRYPTO_RATES: Dict  # Staking { "USDC": "0.035" }
        self.ASSETS: Dict[str, List[Asset]] = {}


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
