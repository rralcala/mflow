from pathlib import Path
from typing import Any, Dict, List, Optional

from asset_classes.asset import Asset
from lib.config import Config, load_config

# Login identity: the profile returns these separately, and the password hash
# never leaves the server.
IDENTITY_KEYS = ("USERNAME", "NAME", "EMAIL", "PASSWORD_HASH")
# Runtime state kept on UserConfig that is not a setting.
PRIVATE_KEYS = ("ASSETS", *IDENTITY_KEYS)
# Keys holding credentials; only whether they are set is exposed.
MASKED_KEY_MARKERS = ("SECRET", "API_KEY")
MASK = "********"


class UserConfig:
    def __init__(self, user_id: str):
        self.USER_ID = user_id
        self.USERNAME = ""
        self.NAME = ""
        self.EMAIL = ""
        self.PASSWORD_HASH = ""
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


def user_config_path(user_id: str, base: Optional[Path] = None) -> Path:
    return Path(base or Config.BASE_PATH) / f"user-{user_id}" / "config.json"


class UserStore:
    user_config = {}

    @staticmethod
    def user_ids() -> List[str]:
        return list(getattr(Config, "USERS", None) or [])

    @staticmethod
    def _load(user_id: str) -> UserConfig:
        if user_id not in UserStore.user_config:
            UserStore.user_config[user_id] = UserConfig(user_id)
            load_config(user_config_path(user_id), UserStore.user_config[user_id])
        return UserStore.user_config[user_id]

    @staticmethod
    def get_user_config(id: str) -> UserConfig:
        return UserStore._load(id)

    @staticmethod
    def find_user_config(user_id: str) -> Optional[UserConfig]:
        """The config of a user listed in USERS, or None. Unlike
        get_user_config this never loads a directory for an unlisted id.
        Login uses it, so tests that mock get_user_config don't affect it."""
        if user_id not in UserStore.user_ids():
            return None
        return UserStore._load(user_id)
