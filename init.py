import argparse
import sys
from pathlib import Path

from flask import Flask
from flask_cors import CORS
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from werkzeug.middleware.proxy_fix import ProxyFix

from lib.config import Config, load_config
from lib.logger import config_logging

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
)

# Parse the arguments
args = parser.parse_args()

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

# Get the absolute path of the current script
script_path = Path(__file__).resolve()
# Get the directory where the script is located
Config.SCRIPT_DIR = script_path.parent

if not load_config(config_file, Config):
    sys.exit(1)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

app.config["SESSION_COOKIE_SAMESITE"] = (
    "Lax"  # Allows the cookie to be sent in top-level navigations
)
app.config["SESSION_COOKIE_SECURE"] = False  # Set to True only if using HTTPS
app.config["SESSION_COOKIE_HTTPONLY"] = True  # Recommended for security
app.config["SESSION_COOKIE_DOMAIN"] = False  # Recommended for security
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path.as_posix()}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = Config.DB_SECRET_KEY

CORS(
    app,
    supports_credentials=True,
    origins=["http://localhost:5173", "http://mflow-test"],
    expose_headers=["X-Total-Count", "Content-Range"],
)
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "auth.login"
logger.info(f"Application initialized successfully.")
