from typing import List, Sequence, Tuple
import csv
import logging
import requests

from asset_classes.fetcher import fetch_if_not_cached
from data.db import Transactions

CRYPTO_PUBLIC_API = "https://api.crypto.com/exchange/v1/public"
CURRENCY_DATA = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json"


def exchange_rate(currencies: str) -> float:
    price = 1.0
    if currencies == "USDPYG":
        if "USDPYG" not in QUOTE_CACHE:
            response = requests.get(CURRENCY_DATA, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "pyg" in data["usd"]:
                    QUOTE_CACHE["USDPYG"] = float(data["usd"]["pyg"])
        price = QUOTE_CACHE["USDPYG"]
    elif currencies == "BTCUSD":
        price, _ = _get_crypto_price("BTCUSD")
    elif currencies == "CROUSD":
        price, _ = _get_crypto_price("CROUSD")
    return price


def fetch_assets(files):
    items = {"USD": [], "PYG": []}
    for file in files:
        logging.debug("Fetching asset data for %s", file)
        fetched = fetch_if_not_cached(file)
        if isinstance(fetched, Sequence):
            for sub_item in fetched:
                items[sub_item.get_currency()].append(sub_item)
        else:
            items[fetched.get_currency()].append(fetched)
    return items


QUOTE_CACHE = {}


def _get_crypto_price(crypto_symbol: str) -> Tuple[float, str]:
    """
    Fetches the current price of a cryptocurrency.
    This is a placeholder function and should be implemented with actual API calls.
    """
    if crypto_symbol in QUOTE_CACHE:
        return QUOTE_CACHE[crypto_symbol]

    url = f"{CRYPTO_PUBLIC_API}/get-valuations?instrument_name={crypto_symbol}-INDEX&valuation_type=index_price&count=1"
    response = requests.get(url, timeout=10)

    if "result" in response.json():
        QUOTE_CACHE[crypto_symbol] = (
            float(response.json()["result"]["data"][0]["v"]),
            "USD",
        )
        return QUOTE_CACHE[crypto_symbol]
    return 0.0, "USD"


def read_net_history() -> List[Tuple[str, float]]:
    ordered_history = []
    t = Transactions()
    for row in t.get_balance_history():
        ordered_history.append(f"{row['month']}-{row['year']}", float(row['amount']))
    return ordered_history


def write_last_net_history(year: str, month: str, amount: float):
    t = Transactions()
    