import threading
import time

from data.exchange_rates import FETCH_LOCK, ExchangeRates
from init import app, debug_mode
from lib.logger import get_logger
from routes import register_api_routes

logger = get_logger()


def background_task():

    while True:
        logger.info("Running...")

        with FETCH_LOCK:
            if len(ExchangeRates.quote_cache) == 0:
                ExchangeRates.fetch_from_local()

            if ExchangeRates.is_stale_or_empty():
                ExchangeRates._refresh_currency_data()

        time.sleep(120)


if __name__ == "__main__":
    t = threading.Thread(target=background_task, daemon=True)
    t.start()
    register_api_routes(app)
    app.run(host="0.0.0.0", debug=debug_mode)
