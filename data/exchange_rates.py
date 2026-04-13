import pickle
from datetime import datetime
from pprint import pprint
from threading import Lock

import requests
import yfinance as yf

from lib.config import Config
from lib.logger import get_logger

logger = get_logger()


CURRENCY_DATA = (
    "https://cdn.jsdelivr.net"
    + "/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json"
)
FX_REFRESH_INTERVAL = 60 * 60  # 1 hours in seconds
TRADED_CRYPTO = ["BTC", "ETH", "SOL", "CRO"]
TRADED_STOCKS = ["VOO", "VTI", "QYLD"]
CURRENCIES = ["pyg"]
FETCH_LOCK = Lock()


class ExchangeRates:
    quote_cache = {}
    currencies = set()
    last_update = datetime.min

    @staticmethod
    def is_stale_or_empty() -> bool:
        """Check if the cached exchange rates are stale based on the last update time."""
        if len(ExchangeRates.quote_cache) == 0:
            return True
        freshness = datetime.now() - ExchangeRates.last_update
        return freshness.total_seconds() > FX_REFRESH_INTERVAL

    @staticmethod
    def _refresh_currency_data():
        """Load currency data from the API and store it in the QUOTE_CACHE."""
        try:
            response = requests.get(CURRENCY_DATA, timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to load currency data: {e}")
            raise e

        currencies = set(CURRENCIES)
        quote_cache = {}
        logger.info(f"Loaded currencies: {', '.join(currencies)}")
        for currency in currencies:
            if currency != "usd":
                key = "USD" + currency.upper()
                if currency in data["usd"]:
                    quote_cache[key] = float(data["usd"][currency])
                    logger.info(
                        f"Loaded exchange rate for {key}: {quote_cache[key]:.8f}"
                    )
                else:
                    logger.warning(
                        f"Exchange rate for {key} not found in API response."
                    )

        currencies.add("usd")
        currencies.add("usdc")

        for crypto in TRADED_CRYPTO:
            key = crypto.upper() + "USD"
            ticker = yf.Ticker(crypto + "-USD")
            ticker.fast_info["last_price"]
            quote_cache[key] = ticker.fast_info["last_price"]
            logger.info(f"Loaded cryto price for {crypto}: {quote_cache[key]:.2f}")

        for stock in TRADED_STOCKS:
            ticker = yf.Ticker(stock)
            quote_cache[stock] = ticker.fast_info["last_price"]
            logger.info(f"Loaded stock price for {stock}: {quote_cache[stock]:.2f}")

        ExchangeRates.currencies = currencies
        ExchangeRates.quote_cache = quote_cache
        ExchangeRates.last_update = datetime.now()
        with open(Config.SCRIPT_DIR / "cache" / "quote_cache.pkl", "wb") as file:
            pickle.dump(ExchangeRates.quote_cache, file)
        with open(Config.SCRIPT_DIR / "cache" / "currencies.pkl", "wb") as file:
            pickle.dump(ExchangeRates.currencies, file)

    @staticmethod
    def ensure_currency_data():
        with FETCH_LOCK:
            if len(ExchangeRates.quote_cache) == 0:
                ExchangeRates.fetch_from_local()
            if len(ExchangeRates.quote_cache) == 0:
                ExchangeRates._refresh_currency_data()

    @staticmethod
    def load_from_db():
        """Load exchange rates from the database and store them in the QUOTE_CACHE."""
        # max_date = Quote.query.with_entities(func.max(Quote.date)).scalar()
        # logger.warning(f"Loading exchange rates from DB, latest date: {max_date}")
        return

    @staticmethod
    def fetch_from_local():
        try:
            cache_path = Config.SCRIPT_DIR / "cache" / "quote_cache.pkl"
            currencies_path = Config.SCRIPT_DIR / "cache" / "currencies.pkl"
            if cache_path.exists() and currencies_path.exists():
                with open(cache_path, "rb") as file:
                    ExchangeRates.load_from_db()
                    # Here we load the quote cache and currencies from the local pickle files. We also update the last_update timestamp based on the file's modification time.
                    ExchangeRates.quote_cache = pickle.load(file)
                    ExchangeRates.last_update = datetime.fromtimestamp(
                        cache_path.stat().st_mtime
                    )

                with open(currencies_path, "rb") as file:
                    ExchangeRates.currencies = pickle.load(file)
                logger.info(
                    f"Loaded exchange rates from cache: {len(ExchangeRates.quote_cache)} rates from {cache_path}"
                )
                return
        except FileNotFoundError:
            ExchangeRates.quote_cache = {}
            ExchangeRates.currencies = set()
            ExchangeRates.last_update = datetime.min
            logger.warning("No cache file found, refreshing currency data.")

    @staticmethod
    def exchange_rate(currencies: str) -> float:
        ExchangeRates.ensure_currency_data()

        """Fetch exchange rate for given currency pair. Including crypto."""
        if currencies.lower() in ExchangeRates.currencies:
            return 1.0
        if currencies in ExchangeRates.quote_cache:
            return ExchangeRates.quote_cache[currencies]
        else:
            raise ValueError(f"Exchange rate for {currencies} not found.")

    @staticmethod
    def get_all() -> dict:
        ExchangeRates.ensure_currency_data()
        return ExchangeRates.quote_cache


if __name__ == "__main__":
    ticker = yf.Ticker("SOL-USD")
    pprint(ticker.fast_info["last_price"])
