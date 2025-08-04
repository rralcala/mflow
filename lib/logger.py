import logging

Logger = logging.getLogger()
is_debug = False


def config_logging(debug: bool):
    global Logger, is_debug
    is_debug = debug
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s:%(levelname)s:%(funcName)s: %(message)s",
    )
    Logger = logging.getLogger()
    return Logger


def log_is_debug():
    global is_debug
    return is_debug


def get_logger() -> logging.Logger:
    global Logger
    return Logger
