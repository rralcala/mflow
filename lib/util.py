from datetime import datetime, timedelta
from typing import Tuple

import requests
from croniter import croniter

CRYPTO_PUBLIC_API = "https://api.crypto.com/exchange/v1/public"


def count_cron_runs(cron_pattern: str, start_date: datetime, end_date: datetime) -> int:
    """
    Counts how many times a cron pattern runs between two dates.
    """
    start = start_date - timedelta(days=1)
    if not cron_pattern:
        return 0
    run_iter = croniter(cron_pattern, start)
    count = 0
    next_run = run_iter.get_next(datetime)
    while next_run <= end_date:
        count += 1
        next_run = run_iter.get_next(datetime)
    return count

QUOTE_CACHE = {}
def get_crypto_price(crypto_symbol: str) -> Tuple[float, str]:
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
