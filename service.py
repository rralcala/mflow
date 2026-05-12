import faulthandler
import signal
import sys
import threading
import time

from flask import request
from werkzeug.routing import BaseConverter, ValidationError

from data.exchange_rates import ExchangeRates
from init import app, initialize_app
from lib.config import Config
from lib.logger import get_logger
from routes import register_api_routes

debug = initialize_app()

if sys.platform == "linux" or sys.platform == "linux2":
    print("Running on Linux")
    faulthandler.register(signal.SIGUSR1)

logger = get_logger()


class IdentifierConverter(BaseConverter):

    def to_python(self, value):
        value = str(value)
        for char in value:
            # Checks if character is between 'a'-'z', 'A'-'Z', or '0'-'9'
            if not (
                ("a" <= char <= "z")
                or ("A" <= char <= "Z")
                or ("0" <= char <= "9")
                or char in "-_"
            ):
                logger.warning(f"Invalid identifier: {value}")
                raise ValidationError()
        return value

    def to_url(self, value):
        value = str(value)
        for char in value:
            # Checks if character is between 'a'-'z', 'A'-'Z', or '0'-'9'
            if not (
                ("a" <= char <= "z")
                or ("A" <= char <= "Z")
                or ("0" <= char <= "9")
                or char in "-_"
            ):
                raise ValidationError()
        return value


app.url_map.converters["identifier"] = IdentifierConverter


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
    app.run(host="0.0.0.0", port=5001, debug=debug)
