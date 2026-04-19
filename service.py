import faulthandler
import signal
import sys
import threading
import time
from datetime import datetime

from data.exchange_rates import FX_FETCH_LOCK, ExchangeRates
from init import app, initialize_app
from lib.config import Config
from lib.logger import get_logger
from models.quotes import Quote
from routes import register_api_routes

initialize_app()

if sys.platform == "linux" or sys.platform == "linux2":
    print("Running on Linux")
    faulthandler.register(signal.SIGUSR1)

logger = get_logger()


def background_task():

    while True:
        logger.info("Running...")
        if Config.DB_SESSION is None:
            time.sleep(1)
            continue
        with FX_FETCH_LOCK:
            if len(ExchangeRates.quote_cache) == 0:
                ExchangeRates.fetch_from_local()

            if ExchangeRates.is_stale_or_empty():
                ExchangeRates._refresh_currency_data()
                with Config.DB_SESSION() as session:
                    date = ExchangeRates.latest_in_db().strftime(
                        Config.DATE_FORMAT_STRING
                    )
                    today = datetime.now().strftime(Config.DATE_FORMAT_STRING)
                    if date is None or date < today:
                        for key, value in ExchangeRates.get_all().items():
                            logger.info(f"Adding quote to DB: {key} = {value:.2f}")
                            date_str = ExchangeRates.last_update.strftime(
                                Config.DATE_FORMAT_STRING
                            )
                            quote = Quote(
                                date=date_str, symbol=key, value=f"{value:.2f}"
                            )
                            session.add(quote)
                        session.commit()
                        logger.info(f"Added Quotes")
        time.sleep(120)


if __name__ == "__main__":
    t = threading.Thread(target=background_task, daemon=True)
    t.start()
    register_api_routes(app)
    app.run(host="0.0.0.0")
