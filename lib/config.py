import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Dict, List

from sqlalchemy.orm import sessionmaker

POSITIVES = "positives"
NEGATIVES = "negatives"


class Config:
    BASE_PATH: Path
    COUNTRIES: List[str]
    CURRENCIES: List[str]
    DB_SESSION: sessionmaker
    SECRET_KEY: str
    SECRET_ALGORITHM = "HS256"
    TRADED_CRYPTO: List[str]
    TRADED_METALS: List[str]
    TRADED_STOCKS: List[str]
    TOKEN_EXPIRATION_HOURS = 24
    LOCAL_SYMBOLS: Dict[str, float]
    # Ids of the users; each one's login and settings are in user-<id>/config.json.
    USERS: List[str]
    YEAR: float = 365.25


# Keys whose values are never logged.
LOG_MASKED_MARKERS = ("SECRET", "PASSWORD", "API_KEY")


def load_config(config_file: Path, dest) -> bool:
    try:
        with config_file.open() as f:
            config_data = json.load(f)

            for key, value in config_data.items():
                setattr(dest, key, value)

                if any(marker in key for marker in LOG_MASKED_MARKERS):
                    logging.info(f"Config: {key} = {'*' * len(str(value))}")
                else:
                    logging.info(f"Config: {key} = {value}")
    except json.JSONDecodeError:
        logging.fatal(f"Error: '%s' is not a valid JSON file.", config_file)
        return False
    except PermissionError:
        logging.fatal("Not enough permissions to open %s", config_file)
        return False
    except FileNotFoundError:
        logging.error("Config file %s does not exist", config_file)
        return False
    return True


def write_json_atomic(path: Path, data: dict) -> None:
    """Replace `path` with `data` as JSON in one step, keeping its permission
    bits, so a crash mid-write can't leave a truncated file."""
    text = json.dumps(data, indent=2) + "\n"
    mode = path.stat().st_mode & 0o777
    try:
        fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=".config-")
    except PermissionError:
        # The directory isn't writable (e.g. only the file is mounted
        # writable); fall back to rewriting the file in place.
        path.write_text(text)
        return
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp_name, mode)
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


# Keys that must be present in the main config.json for the API to work.
REQUIRED_KEYS = ("COUNTRIES", "USERS")


def invalid_user_ids(config) -> list:
    """USERS entries that can't name a user-<id> directory."""
    return [
        uid
        for uid in getattr(config, "USERS", None) or []
        if not (isinstance(uid, str) and uid.isalnum())
    ]


def missing_required_keys(config) -> List[str]:
    """Names of REQUIRED_KEYS that are absent from, or not a list in, `config`."""
    return [
        key for key in REQUIRED_KEYS if not isinstance(getattr(config, key, None), list)
    ]
