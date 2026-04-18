from datetime import datetime
from threading import Lock
from typing import List, Tuple

import requests
import yfinance as yf
from sqlalchemy import func

from init import Session
from lib.config import Config
from lib.logger import get_logger
from models.quotes import Quote

logger = get_logger()


CURRENCY_DATA = (
    "https://cdn.jsdelivr.net"
    + "/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json"
)
FX_REFRESH_INTERVAL = 60 * 60  # 1 hours in seconds

FX_FETCH_LOCK = Lock()


class ExchangeRates:
    quote_cache = {}
    currencies = set(Config.CURRENCIES)
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

        quote_cache = {}
        for currency in ExchangeRates.currencies:
            if currency != "usd":
                key = "USD" + currency.upper()
                if currency in data["usd"]:
                    quote_cache[key] = round(float(data["usd"][currency]), 2)
                    logger.info(f"Loaded exchange rate for {key}: {quote_cache[key]}")
                else:
                    logger.warning(
                        f"Exchange rate for {key} not found in API response."
                    )

        for crypto in Config.TRADED_CRYPTO:
            key = crypto.upper() + "USD"
            ticker = yf.Ticker(crypto + "-USD")
            ticker.fast_info["last_price"]
            quote_cache[key] = round(ticker.fast_info["last_price"], 4)
            logger.info(f"Loaded cryto price for {crypto}: {quote_cache[key]}")

        for stock in Config.TRADED_STOCKS:
            ticker = yf.Ticker(stock)
            quote_cache[stock] = round(ticker.fast_info["last_price"], 2)
            logger.info(f"Loaded stock price for {stock}: {quote_cache[stock]}")

        ExchangeRates.quote_cache = quote_cache
        ExchangeRates.last_update = datetime.now()

    @staticmethod
    def latest_in_db() -> datetime:
        with Session() as session:
            date = session.query(func.max(Quote.date)).scalar()
        if date is None:
            date = datetime.min
        else:
            date = datetime.strptime(date, Config.DATE_FORMAT_STRING)
        return date

    @staticmethod
    def local_quotes_on(date: str) -> List[Tuple[str, float]]:
        with Session() as session:
            quotes = session.query(Quote).filter(Quote.date == date).all()
            results = []
            for quote in quotes:
                logger.info(f"Loaded quote from DB: {quote.symbol} = {quote.value}")
                results.append((quote.symbol, round(float(quote.value), 4)))
        return results

    @staticmethod
    def ensure_currency_data():
        if FX_FETCH_LOCK.locked():
            return
        with FX_FETCH_LOCK:
            if len(ExchangeRates.quote_cache) == 0:
                ExchangeRates.fetch_from_local()
            if len(ExchangeRates.quote_cache) == 0:
                ExchangeRates._refresh_currency_data()

    @staticmethod
    def fetch_from_local():
        date = ExchangeRates.latest_in_db().strftime(Config.DATE_FORMAT_STRING)

        for symbol, value in ExchangeRates.local_quotes_on(date):
            logger.info(f"Loaded quote from DB: {symbol} = {value}")
            ExchangeRates.quote_cache[symbol] = value

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
    print(ticker.fast_info["last_price"])
