import json
import logging
from pathlib import Path
from typing import Dict, List

from sqlalchemy.orm import sessionmaker


class Config:
    BASE_PATH: Path
    DATE_FORMAT_STRING = "%Y-%m-%d"
    SECRET_KEY: str
    SCRIPT_DIR: Path
    YEAR: float = 365.25
    USERS: Dict
    TRADED_CRYPTO: List[str]
    TRADED_STOCKS: List[str]
    CURRENCIES: List[str]
    DB_SESSION: sessionmaker


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
