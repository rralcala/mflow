"""Internal data handling functions."""

import logging
from typing import Tuple

import requests

CRYPTO_PUBLIC_API = "https://api.crypto.com/exchange/v1/public"
CURRENCY_DATA = (
    "https://cdn.jsdelivr.net"
    + "/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json"
)
QUOTE_CACHE = {}


def exchange_rate(currencies: str) -> float:
    """Fetch exchange rate for given currency pair. Including crypto."""
    if currencies == "USDPYG":
        if "USDPYG" not in QUOTE_CACHE:
            response = requests.get(CURRENCY_DATA, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "pyg" in data["usd"]:
                    QUOTE_CACHE["USDPYG"] = float(data["usd"]["pyg"])
            else:
                logging.error(
                    "Failed to fetch exchange rate for USDPYG: %s: %s",
                    response.status_code,
                    response.text,
                )
        return QUOTE_CACHE["USDPYG"]
    elif currencies == "BTCUSD":
        return _get_crypto_price("BTCUSD")[0]
    elif currencies == "SOLUSD":
        return _get_crypto_price("SOLUSD")[0]
    elif currencies == "CROUSD":
        return _get_crypto_price("CROUSD")[0]
    else:
        raise ValueError(f"Unknown currency pair {currencies}")


def _get_crypto_price(crypto_symbol: str) -> Tuple[float, str]:
    """
    Fetches the current price of a cryptocurrency.
    This is a placeholder function and should be implemented with actual API calls.
    """
    if crypto_symbol in QUOTE_CACHE:
        return QUOTE_CACHE[crypto_symbol]

    url = (
        CRYPTO_PUBLIC_API
        + "/get-valuations?instrument_name="
        + crypto_symbol
        + "-INDEX&valuation_type=index_price&count=1"
    )
    response = requests.get(url, timeout=10)

    if "result" in response.json():
        QUOTE_CACHE[crypto_symbol] = (
            float(response.json()["result"]["data"][0]["v"]),
            "USD",
        )
        return QUOTE_CACHE[crypto_symbol]
    return 0.0, "USD"
