from typing import Any, Dict, List

from asset_classes.asset import Asset
from lib.config import Config, load_config

# Runtime state kept on UserConfig that is not a setting.
PRIVATE_KEYS = ("ASSETS",)
# Keys holding credentials; only whether they are set is exposed.
MASKED_KEY_MARKERS = ("SECRET", "API_KEY")
MASK = "********"


class UserConfig:
    def __init__(self, user_id: str):
        self.USER_ID = user_id
        self.SECONDARY_CURRENCY = ""
        self.SECONDARY_COUNTRY = "PY"
        self.LAST_UNTIL = "2075-01-01"
        self.DESIRED_ESTATE = 0.0
        # Yearly inflation per country, used by the future timeline projection.
        self.INFLATION_RATES: Dict[str, float] = {"US": 0.025, "UY": 0.025, "PY": 0.035}
        self.COINBASE_API_KEY = ""
        self.COINBASE_API_SECRET = ""
        self.COINBASE_PORTFOLIO_ID = ""
        self.CRYPTO_RATES: Dict  # Staking { "USDC": "0.035" }
        # Recurrents whose remaining monthly budget shows on the dashboard,
        # e.g. [{"id": "Discretionary", "label": "discretionary"}].
        self.DASHBOARD_RECURRENTS: List[Dict[str, str]] = []
        self.ASSETS: Dict[str, List[Asset]] = {}

    def to_public_dict(self) -> Dict[str, Any]:
        """Settings safe to send to the client: credentials are masked and the
        runtime asset cache is left out."""
        public = {}
        for key, value in sorted(vars(self).items()):
            if key in PRIVATE_KEYS:
                continue
            if any(marker in key for marker in MASKED_KEY_MARKERS):
                value = MASK if value else ""
            public[key] = value
        return public


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
