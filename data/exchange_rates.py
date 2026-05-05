import os
import pickle
from datetime import datetime
from threading import Lock
from typing import List, Tuple

import requests
import yfinance as yf
from sqlalchemy import func, select

from lib.config import Config
from lib.logger import get_logger
from models.quotes import Quote

Logger = get_logger()


CURRENCY_DATA = (
    "https://cdn.jsdelivr.net"
    + "/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json"
)
FX_REFRESH_INTERVAL = 60 * 60  # 1 hours in seconds
FX_LAST_UPDATE_FILE = "cache/last_fx_refresh.pkl"
FX_FETCH_LOCK = Lock()


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
            Logger.error(f"Failed to load currency data: {e}")
            raise e

        quote_cache = {}
        for currency in ExchangeRates.currencies:
            if currency != "usd":
                key = "USD" + currency.upper()
                if currency in data["usd"]:
                    quote_cache[key] = round(float(data["usd"][currency]), 2)
                    Logger.info(f"Loaded exchange rate for {key}: {quote_cache[key]}")
                else:
                    Logger.warning(
                        f"Exchange rate for {key} not found in API response."
                    )

        for crypto in Config.TRADED_CRYPTO:
            key = crypto.upper() + "USD"
            ticker = yf.Ticker(crypto + "-USD")
            ticker.fast_info["last_price"]
            quote_cache[key] = round(ticker.fast_info["last_price"], 4)
            Logger.info(f"Loaded cryto price for {crypto}: {quote_cache[key]}")

        for stock in Config.TRADED_STOCKS:
            ticker = yf.Ticker(stock)
            quote_cache[stock] = round(ticker.fast_info["last_price"], 2)
            Logger.info(f"Loaded stock price for {stock}: {quote_cache[stock]}")
        quote_cache["UYAM"] = 1.0
        ExchangeRates.currencies = set(Config.CURRENCIES)
        ExchangeRates.quote_cache = quote_cache
        ExchangeRates.last_update = datetime.now()

    @staticmethod
    def latest_in_db() -> datetime:
        with Config.DB_SESSION() as session:
            date = session.query(func.max(Quote.date)).scalar()
        if date is None:
            date = datetime.min
        else:
            date = datetime.strptime(date, Config.DATE_FORMAT_STRING)
        return date

    @staticmethod
    def local_quotes_on(date: str) -> List[Tuple[str, float]]:
        with Config.DB_SESSION() as session:
            quotes = session.query(Quote).filter(Quote.date == date).all()
            results = []
            for quote in quotes:
                Logger.info(f"Loaded quote from DB: {quote.symbol} = {quote.value}")
                results.append((quote.symbol, round(float(quote.value), 4)))
        return results

    @staticmethod
    def ensure_currency_data():
        if FX_FETCH_LOCK.locked():
            return
        with FX_FETCH_LOCK:
            if len(ExchangeRates.currencies) == 0:
                Logger.warning("Currency set is empty, loading from config...")
                ExchangeRates.currencies = set(Config.CURRENCIES)
            if len(ExchangeRates.quote_cache) == 0:
                ExchangeRates.fetch_from_local()
            if len(ExchangeRates.quote_cache) == 0:
                ExchangeRates._refresh_currency_data()

    @staticmethod
    def fetch_from_local():
        date = ExchangeRates.latest_in_db()
        date_str = date.strftime(Config.DATE_FORMAT_STRING)
        for symbol, value in ExchangeRates.local_quotes_on(date_str):

            ExchangeRates.quote_cache[symbol] = value
        if os.path.exists(FX_LAST_UPDATE_FILE):
            with open(FX_LAST_UPDATE_FILE, "rb") as f:
                last_run = pickle.load(f)
            if last_run.date() == date.date():
                ExchangeRates.last_update = last_run
            else:
                ExchangeRates.last_update = date
        else:
            ExchangeRates.last_update = date
        ExchangeRates.currencies = set(Config.CURRENCIES)
        Logger.info(f"Loaded quotes: {date_str} freshness {ExchangeRates.last_update}")

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
    def background_refresh():
        with FX_FETCH_LOCK:
            if len(ExchangeRates.quote_cache) == 0:
                ExchangeRates.fetch_from_local()

            if ExchangeRates.is_stale_or_empty():
                Logger.info("Refreshing exchange rates...")
                ExchangeRates._refresh_currency_data()
                with Config.DB_SESSION() as session:
                    date = ExchangeRates.latest_in_db().strftime(
                        Config.DATE_FORMAT_STRING
                    )
                    today = datetime.now().strftime(Config.DATE_FORMAT_STRING)
                    if True:  # date is None or date < today:
                        for key, value in ExchangeRates.get_all().items():
                            Logger.info(f"Adding quote to DB: {key} = {value:.2f}")
                            date_str = ExchangeRates.last_update.strftime(
                                Config.DATE_FORMAT_STRING
                            )
                            quote = session.scalars(
                                select(Quote).filter_by(date=date_str, symbol=key)
                            ).one_or_none()
                            if quote is None:
                                quote = Quote(
                                    date=date_str, symbol=key, value=f"{value:.2f}"
                                )
                            session.merge(quote)
                        session.commit()
                        with open(FX_LAST_UPDATE_FILE, "wb") as f:
                            pickle.dump(datetime.now(), f)
                        Logger.info(f"Added Quotes")

    @staticmethod
    def get_all() -> dict:
        ExchangeRates.ensure_currency_data()
        return ExchangeRates.quote_cache
