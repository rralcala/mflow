import argparse
import logging
import sys
from pathlib import Path

from apiflask import APIFlask
from flask_cors import CORS
from flask_login import LoginManager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from werkzeug.middleware.proxy_fix import ProxyFix

from lib.config import Config, invalid_user_ids, load_config, missing_required_keys
from lib.logger import config_logging

# Created unbound so route modules can register their handlers at import time;
# create_app() attaches it to the app.
login_manager = LoginManager()
login_manager.login_view = "auth.login"
logger = logging.getLogger()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Process a JSON configuration file.")

    parser.add_argument(
        "--base",
        type=str,
        required=True,
        help="Path to the base directory (e.g., /etc/mflow/)",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Verbose logging and interactive API docs/spec",
    )

    return parser.parse_args(argv)


def create_app(debug: bool = False) -> APIFlask:
    """Build the Flask app. Expects Config to be loaded already."""
    # Interactive docs/spec are only served in debug mode. APIFlask decides this
    # at construction, so the app is built after the arguments are parsed.
    app = APIFlask(
        __name__,
        title="mflow",
        version="1.0",
        enable_openapi=debug,
    )
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    app.config["SESSION_COOKIE_SAMESITE"] = (
        "Lax"  # Allows the cookie to be sent in top-level navigations
    )
    app.config["SESSION_COOKIE_SECURE"] = False  # Set to True only if using HTTPS
    app.config["SESSION_COOKIE_HTTPONLY"] = True  # Recommended for security
    app.config["SESSION_COOKIE_DOMAIN"] = False  # Recommended for security
    app.secret_key = Config.SECRET_KEY
    CORS(
        app,
        supports_credentials=True,
        origins=["http://localhost:5173", "http://mflow-test"],
        expose_headers=["X-Total-Count", "Content-Range"],
    )
    login_manager.init_app(app)

    # Imported here: the routes package imports this module.
    from routes.errors import configure_errors
    from routes.security import add_cookie_security, security_schemes

    configure_errors(app)
    app.config["SECURITY_SCHEMES"] = security_schemes(app.config["SESSION_COOKIE_NAME"])
    app.spec_processor(add_cookie_security)
    return app


def initialize_app(argv: list[str] | None = None) -> APIFlask:
    global logger
    args = parse_args(argv)
    logger = config_logging(debug=args.debug)

    Config.BASE_PATH = Path(args.base)
    db_path = Config.BASE_PATH / "mydatabase.db"
    if not db_path.exists():
        logger.fatal(f"Error: The file '{str(db_path)}' does not exist.")
        sys.exit(1)

    config_file = Config.BASE_PATH / "config.json"
    # Path validation logic
    if not config_file.exists():
        logger.fatal(f"Error: The file '{config_file}' does not exist.")
        sys.exit(1)

    if not load_config(config_file, Config):
        sys.exit(1)

    missing = missing_required_keys(Config)
    if missing:
        logger.fatal(f"Error: '{config_file}' is missing required key(s): {missing}")
        if "USERS" in missing:
            logger.fatal(
                "USERS must be a list of user ids. If it still holds logins, run "
                "python -m scripts.split_user_config --base <data dir>"
            )
        sys.exit(1)

    invalid = invalid_user_ids(Config)
    if invalid:
        logger.fatal(f"Error: USERS ids must be alphanumeric strings: {invalid}")
        sys.exit(1)

    app = create_app(debug=args.debug)

    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    Config.DB_SESSION = sessionmaker(bind=engine)
    logger.info("Application initialized successfully.")
    return app
