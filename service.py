import argparse
import json
import logging
import os
import socket
import sys
from pathlib import Path

from flask import (Flask, flash, make_response, redirect, render_template,
                   request, url_for)
from flask_admin import Admin
from flask_admin.base import Bootstrap4Theme
from flask_login import (LoginManager, UserMixin, login_user,
                         logout_user)
from flask_sqlalchemy import SQLAlchemy

from data.asset_store import load_assets
from lib.config import Config
from lib.custom_views import (AnalyticsView, MyAdminIndexView,
                              RecurrentModelView)
from lib.util import sha256_hash
from views import cash_flow as vcf
from views import investment_performance as vip
from views import list_assets as vla
from views import upcoming_payments as vup
from views.monthly_pnl import monthly_pnl as vmpnl

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
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{Config.BASE_PATH}mydatabase.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "mysecretkey123"
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

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


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)

    def set_password(self, password):
        self.password = sha256_hash(password)

    def check_password(self, password):
        logging.warning(
            f"Checking password for user {self.username} {self.password} against {sha256_hash(password)}"
        )
        return self.password == sha256_hash(password)


@app.route("/monthly-pnl")
def monthly_pnl():
    include_income = request.args.get("income", "0") == "1"
    include_expenses = request.args.get("expenses", "0") == "1"

    global ASSETS
    if not ASSETS:
        ASSETS = load_assets(Recurrent)
    response = make_response(vmpnl(ASSETS, include_income, include_expenses), 200)
    response.mimetype = "text/plain"

    return response


@app.route("/reload")
def reload_assets():
    global ASSETS
    ASSETS = load_assets(Recurrent)
    return make_response("Assets reloaded", 200)


@app.route("/investment-performance")
def investment_performance():
    global ASSETS
    if not ASSETS:
        ASSETS = load_assets(Recurrent)
    return vip.investment_performance(ASSETS)


@app.route("/cash-flow-detail")
def cash_flow():
    global ASSETS
    if not ASSETS:
        ASSETS = load_assets(Recurrent)
    return vcf.cash_flow(ASSETS)


@app.route("/upcoming-payments")
def upcoming_payments():
    exclude_capital = request.args.get("exclude", "0") == "1"
    global ASSETS
    if not ASSETS:
        ASSETS = load_assets(Recurrent)
    return vup.upcoming_payments(ASSETS, exclude_capital)


@app.route("/list-assets")
def list_assets():
    global ASSETS
    if not ASSETS:
        ASSETS = load_assets(Recurrent)
    return vla.list_assets(ASSETS)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("admin.index"))
        else:
            flash("Invalid username or password")

    return render_template("login.html")


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("login"))


if __name__ == "__main__":

    admin = Admin(
        app,
        name="mflow",
        index_view=MyAdminIndexView(),
        theme=Bootstrap4Theme(swatch="cerulean"),
    )

    admin.add_view(AnalyticsView(name="Analytics", endpoint="analytics"))
    admin.add_view(RecurrentModelView(Recurrent, db.session))
    app.run(host="0.0.0.0")
