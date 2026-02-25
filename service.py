import argparse
import io
import json
import logging
import os
import socket
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dateutil.relativedelta import relativedelta
from flask import Flask, make_response, request
from flask_admin import Admin, BaseView, expose
from flask_admin.base import Bootstrap4Theme
from flask_admin.contrib.sqla import ModelView
from flask_sqlalchemy import SQLAlchemy

from asset_classes.fetcher import fetch_assets
from asset_classes.instrument import Instrument
from asset_classes import recurrent
from data import asset_store
from data.coinbase import get_accounts
from lib.config import Config
from lib.pk_model_view import RecurrentModelView
from reports.cash_flow import generate_timeline
from views import \
    cash_flow as vcf  # noqa: F401 - import for side-effects to register routes
from views import investment_performance as vip
from views import list_assets as vla
from views import \
    upcoming_payments as \
    vup  # noqa: F401 - import for side-effects to register routes
from views.monthly_pnl import \
    monthly_pnl as \
    vmpnl  # noqa: F401 - import for side-effects to register routes

# from views.cash_flow import cash_flow  # noqa: F401 - import for side-effects to register route
ASSETS = None

hostname = socket.gethostname()
logging.warning(f"Hostname: {hostname}")
parser = argparse.ArgumentParser(description="Process a JSON configuration file.")

parser.add_argument(
    "--base",
    type=str,
    required=True,
    help="Path to the base directory (e.g., /etc/mflow/)",
)
# Parse the arguments
args = parser.parse_args()

# Path validation logic
if not os.path.exists(args.base + "/config.json"):
    logging.fatal(f"Error: The file '{args.config}' does not exist.")
    sys.exit(1)

Config.BASE_PATH = args.base + "/"
# Get the absolute path of the current script
script_path = Path(__file__).resolve()
# Get the directory where the script is located
Config.SCRIPT_DIR = script_path.parent

try:
    with open(Config.BASE_PATH + "config.json", "r") as f:
        config_data = json.load(f)
        

        for key, value in config_data.items():
            setattr(Config, key, value)
except json.JSONDecodeError:
    print(f"Error: '{args.config}' is not a valid JSON file.")

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{Config.BASE_PATH}mydatabase.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'mysecretkey123'
db = SQLAlchemy(app)

# 3. Define a Model
class Recurrent(db.Model):
    identifier = db.Column(db.String(80), primary_key=True)
    parent_asset_id = db.Column(db.String(80), nullable=True)
    country = db.Column(db.String(2), nullable=False)
    amount = db.Column(db.String(20), nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    recurrence = db.Column(db.String(20), nullable=False)
    start = db.Column(db.String(20), nullable=False)
    end = db.Column(db.String(20), nullable=False)
    flow_class = db.Column(db.String(20), nullable=False)
    rate = db.Column(db.String(20), nullable=False)
    def __str__(self):
        return self.identifier

def load_assets():
    global ASSETS
    ASSETS = asset_store.load_assets(fetch_assets, Config.BASE_PATH, "gdrive_key.json")
    append_cb(ASSETS)

    for row in Recurrent.query.all():
        asset = recurrent.Recurrent(
            identifier=str(row.identifier),
            parent_asset_id=str(row.parent_asset_id),
            country=row.country,
            amount=float(row.amount),
            currency=str(row.currency),
            recurrence=row.recurrence,
            start=row.start,
            end=row.end,
            flow_class=row.flow_class,
            rate=float(row.rate),
        )
        ASSETS[asset.currency].append(asset)


def append_cb(assets):
    for position in get_accounts(
        Config.COINBASE_API_KEY,
        Config.COINBASE_API_SECRET,
        Config.COINBASE_PORTFOLIO_ID,
    ):
        if position["asset"] == "USDC":
            qty = float(position["total_balance_crypto"])
            rate = 0.045
            account = Instrument(
                location="Coinbase",
                symbol="USDC",
                price=1.0,
                factor=1.0,
                qty=qty,
                estimated_dividend=qty * rate / 12,
                rate=rate,
                dividend="0 0 1 * *",
                currency="USD",
                acquisition_date=datetime(2025, 9, 24),
                acquisition_price=1.0,
                liquid=True,
            )
            assets["USD"].append(account)
        if position["asset"] == "SOL":
            qty = float(position["total_balance_crypto"])
            rate = 0.0424
            account = Instrument(
                location="Coinbase",
                symbol="SOLUSD",
                price=float(position["total_balance_fiat"]) / qty,
                factor=1.0,
                qty=qty,
                estimated_dividend=qty * rate / 12,
                rate=rate,
                dividend="0 0 1 * *",
                currency="USD",
                acquisition_date=datetime(2025, 9, 24),
                acquisition_price=float(position["cost_basis"]["value"]) / qty,
                liquid=False,
            )
            assets["USD"].append(account)

        if position["asset"] == "ETH":
            qty = float(position["total_balance_crypto"])
            rate = 0.0
            account = Instrument(
                location="Coinbase",
                symbol="ETHUSD",
                price=float(position["total_balance_fiat"]) / qty,
                factor=1.0,
                qty=qty,
                estimated_dividend=qty * rate / 12,
                rate=rate,
                dividend="0 0 1 * *",
                currency="USD",
                acquisition_date=datetime(2026, 2, 10),
                acquisition_price=float(position["cost_basis"]["value"]) / qty,
                liquid=False,
            )
            assets["USD"].append(account)


class AnalyticsView(BaseView):
    @expose("/")
    def index(self):
        return self.render("analytics_index.html")


@app.route("/monthly-pnl")
def monthly_pnl():
    include_income = request.args.get("income", "0") == "1"
    include_expenses = request.args.get("expenses", "0") == "1"
    
    global ASSETS
    if not ASSETS:
        load_assets()
    output = vmpnl(ASSETS, include_income, include_expenses)
    response = make_response(output.getvalue(), 200)
    response.mimetype = "text/plain"
    output.close()
    return response


@app.route("/reload")
def reload_assets():
    global ASSETS
    load_assets()
    return make_response("Assets reloaded", 200)


@app.route("/investment-performance")
def investment_performance():
    global ASSETS
    if not ASSETS:
        load_assets()
    return vip.investment_performance(ASSETS)


@app.route("/cash-flow-detail")
def cash_flow():
    global ASSETS
    if not ASSETS:
        load_assets()
    return vcf.cash_flow(ASSETS)


@app.route("/upcoming-payments")
def upcoming_payments():
    exclude_capital = request.args.get("exclude", "0") == "1"
    global ASSETS
    if not ASSETS:
        load_assets()
    return vup.upcoming_payments(ASSETS, exclude_capital)


@app.route("/list-assets")
def list_assets():
    global ASSETS
    if not ASSETS:
        load_assets()
    return vla.list_assets(ASSETS)


if __name__ == "__main__":
 

    admin = Admin(app, name="mflow", theme=Bootstrap4Theme(swatch="cerulean"))

    admin.add_view(AnalyticsView(name="Analytics", endpoint="analytics"))
    admin.add_view(RecurrentModelView(Recurrent, db.session))
    app.run(host='0.0.0.0')
