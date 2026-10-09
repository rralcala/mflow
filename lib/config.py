import json
import logging
from pathlib import Path
from typing import Dict, List

from sqlalchemy.orm import sessionmaker

POSITIVES = "positives"
NEGATIVES = "negatives"


class Config:
    BASE_PATH: Path
    COUNTRIES: List[str]
    CURRENCIES: List[str]
    DATE_FORMAT_STRING = "%Y-%m-%d"
    DB_SESSION: sessionmaker
    SECRET_KEY: str
    TRADED_CRYPTO: List[str]
    TRADED_METALS: List[str]
    TRADED_STOCKS: List[str]
    LOCAL_SYMBOLS: Dict[str, float]
    USERS: Dict
    YEAR: float = 365.25


def load_config(config_file: Path, dest) -> bool:
    try:
        with config_file.open() as f:
            config_data = json.load(f)

            for key, value in config_data.items():
                setattr(dest, key, value)

                if "SECRET" in key:
                    logging.info(f"Config: {key} = {'*' * len(str(value))}")
                else:
                    logging.info(f"Config: {key} = {value}")
    except json.JSONDecodeError:
        logging.fatal(f"Error: '%s' is not a valid JSON file.", config_file)
        return False
    except PermissionError:
        logging.fatal("Not enough permissions to open %s", config_file)
        return False
    return True


# Keys that must be present in the main config.json for the API to work.
REQUIRED_KEYS = ("COUNTRIES",)


def missing_required_keys(config) -> List[str]:
    """Names of REQUIRED_KEYS that are absent from, or not a list in, `config`."""
    return [
        key for key in REQUIRED_KEYS if not isinstance(getattr(config, key, None), list)
    ]
