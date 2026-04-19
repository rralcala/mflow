import faulthandler
import signal
import sys
import threading
import time
from datetime import datetime

from data.exchange_rates import ExchangeRates
from init import app, initialize_app
from lib.config import Config
from lib.logger import get_logger
from models.quotes import Quote
from routes import register_api_routes

debug = initialize_app()

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

        ExchangeRates.background_refresh()
        time.sleep(120)


if __name__ == "__main__":
    t = threading.Thread(target=background_task, daemon=True)
    t.start()
    register_api_routes(app)
    app.run(host="0.0.0.0", debug=debug)
