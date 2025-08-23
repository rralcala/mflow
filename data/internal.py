from typing import List, Tuple
import csv
import logging
import requests

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
        QUOTE_CACHE[crypto_symbol] = float(response.json()["result"]["data"][0]["v"]), "USD"
        return QUOTE_CACHE[crypto_symbol]
    return 0.0, "USD"

def read_net_history() -> List[Tuple[str, float]]:
    ordered_history = []
    with open("history.csv", "r", encoding="utf-8") as csvfile:
        # Create a reader object
        csv_reader = csv.reader(csvfile)
        # Iterate through each row in the CSV file
        for row in csv_reader:
            ordered_history.append([row[0], float(row[1].replace(",", ""))])
    return ordered_history

def write_net_history(ordered_history):
    with open("history.csv", "w", encoding="utf-8") as file:
        writer = csv.writer(file)
        for _, row in enumerate(ordered_history):
            new_row = [row[0], f"{row[1]:,.2f}"]
            logging.debug("Writing to history: %s", new_row)
            writer.writerow(new_row)
