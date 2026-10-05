import logging

Logger = logging.getLogger()


def config_logging(debug: bool):
    global Logger
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s:%(levelname)s:%(funcName)s: %(message)s",
    )
    Logger = logging.getLogger()
    return Logger


def get_logger() -> logging.Logger:
    return Logger
