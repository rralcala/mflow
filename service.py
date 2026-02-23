import io
import json
import logging
from datetime import datetime, timedelta, timezone

from dateutil.relativedelta import relativedelta
from flask import Flask, make_response, request
from flask_admin import Admin, BaseView, expose
from flask_admin.base import Bootstrap4Theme

from asset_classes.fetcher import fetch_assets
from asset_classes.instrument import Instrument
from data.asset_store import load_assets
from data.coinbase import get_accounts
from data.internal import exchange_rate
from lib import config, util
from reports.cash_flow import generate_timeline
from reports.list_assets import list_assets as r_list_assets

# from views.cash_flow import cash_flow  # noqa: F401 - import for side-effects to register route
ASSETS = None


app = Flask(__name__)
admin = Admin(app, name="mflow", theme=Bootstrap4Theme(swatch="cerulean"))

with open(config.BASE_PATH + "cdp_api_key.json", "r") as file:
    content = json.loads(file.read())
    config.COINBASE_API_KEY = content.get("name", "")
    config.COINBASE_API_SECRET = content.get("privateKey", "")
    config.COINBASE_PORTFOLIO_ID = content.get("portfolioId", "")


def append_cb(assets):
    for position in get_accounts(
        config.COINBASE_API_KEY,
        config.COINBASE_API_SECRET,
        config.COINBASE_PORTFOLIO_ID,
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


@app.route("/monthly-pnl")
def monthly_pnl():
    include_income = request.args.get("income", "0") == "1"
    include_expenses = request.args.get("expenses", "0") == "1"
    logging.warning(f"Exchange Rate: {exchange_rate('USDPYG')}")
    global ASSETS
    if not ASSETS:
        ASSETS = load_assets(fetch_assets, config.BASE_PATH, "key.json")
        append_cb(ASSETS)
    start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    output = io.StringIO()

    grand_totals = {"USD": 0.0, "PYG": 0.0}
    for _ in range(12):
        nsums = {}
        psums = {}
        expenses_str = io.StringIO()
        income_str = io.StringIO()
        for currency, assets in ASSETS.items():
            nsums[currency] = 0.0
            psums[currency] = 0.0
            for asset in assets:
                income = asset.get_income(start, include_capital=False)
                if income[0] < 0.0:
                    expenses_str.write(
                        asset.identifier + ": " + f"{income[0]:,.2f} {income[1]}\n"
                    )
                    nsums[currency] += income[0]
                elif income[0] > 0.0:
                    psums[currency] += income[0]
                    income_str.write(
                        asset.identifier + ": " + f"{income[0]:,.2f} {income[1]}\n"
                    )
        output.write(f"\n== {start.strftime("%Y %B")} ==\n")
        output.write("\n")
        if include_income:
            income_str.seek(0)
            output.write(income_str.read() + "\n")
            income_str.close()
        if include_expenses:
            expenses_str.seek(0)
            output.write(expenses_str.read() + "\n")
            expenses_str.close()

        output.write(
            f"Income:   {psums['PYG']:>12,.0f} Income:   {psums['USD']:>12,.2f}\n"
        )
        output.write(
            f"Expenses: {nsums['PYG']:>12,.0f} Expenses: {nsums['USD']:>12,.2f}\n"
        )
        output.write(
            f"Total:    {psums['PYG'] + nsums['PYG']:>12,.0f} Total:    {psums['USD'] + nsums['USD']:>12,.2f}\n"
        )
        grand_totals["PYG"] += psums["PYG"] + nsums["PYG"]
        grand_totals["USD"] += psums["USD"] + nsums["USD"]
        start = start + relativedelta(months=1)
    output.write(
        f"\nGrand Totals: PYG {grand_totals['PYG']:12,.0f}\n              USD    {grand_totals['USD']:12,.2f}\n\n"
    )
    output.write(
        f"Net:          PYG {(grand_totals['PYG'] + grand_totals['USD']*exchange_rate("USDPYG")):12,.0f}\n"
    )
    response = make_response(output.getvalue(), 200)
    response.mimetype = "text/plain"
    return response


@app.route("/list-assets")
def list_assets():
    global ASSETS
    if not ASSETS:
        ASSETS = load_assets(fetch_assets, config.BASE_PATH, "key.json")
        append_cb(ASSETS)
    a, b, c = r_list_assets(ASSETS, print_pos=True, print_neg=True)

    sum = 0.0
    for item in a:
        sum += item[1] + item[2]

    grand_total = sum
    ret = 0.0
    for current_value, current_return, _ in b:
        tret = (current_value / grand_total) * current_return
        ret += tret
    response = make_response(
        util.PRINTER.pformat(c)
        + f"\n\nReturn: {(ret*100):,.2f}%\n\nEstimated Monthly: {sum*ret/12:,.2f}$\n\nTotal: {sum:,.2f}$",
        200,
    )
    response.mimetype = "text/plain"
    return response


@app.route("/cash-month-detail")
def month_flow():
    assets = load_assets(fetch_assets, config.BASE_PATH, "key.json")
    end_dt = datetime.now() + timedelta(days=365)
    months = {}
    target_month_date = datetime.now()
    for i in range(13):
        months[(target_month_date + relativedelta(months=i)).strftime("%Y-%m")] = {
            "USD-US": 0.0,
            "USD-PY": 0.0,
            "PYG-PY": 0.0,
        }
    payments = []
    for country, tl in generate_timeline(assets, end_dt):
        for entry in tl:
            d, (amount, currency) = entry
            dt = datetime(d.year, d.month, d.day)
            if dt.tzinfo is None:
                dt_aware = dt.replace(tzinfo=timezone.utc)
            else:
                dt_aware = dt.astimezone(timezone.utc)
            payment = {
                "country": country,
                "date": dt_aware.strftime("%Y-%m"),
                "amount": amount,
                "currency": currency,
            }
            months[payment["date"]][
                f"{payment['currency']}-{payment['country']}"
            ] += payment["amount"]

    timeline = {}
    payments = sorted(payments, key=lambda x: (x["date"], x["country"]))
    uu = 0.0
    up = 0.0
    pp = 0.0
    for payment in payments:
        key = payment["date"]
        timeline.setdefault(key, {"USD-US": uu, "USD-PY": up, "PYG-PY": pp})
        timeline[key][f"{payment['currency']}-{payment['country']}"] += payment[
            "amount"
        ]
        uu = timeline[key]["USD-US"]
        up = timeline[key]["USD-PY"]
        pp = timeline[key]["PYG-PY"]

    output = io.StringIO()
    output.write(
        f'<table><tr><th>Date</th><th style="text-align: right;">USD-US</th><th style="text-align: right;">USD-PY</th><th style="text-align: right;">PYG-PY</th></tr>\n'
    )
    for date, amounts in months.items():

        output.write(
            f"<tr><td>{date}</td><td style=\"text-align: right;\">{amounts['USD-US']:,.2f}</td><td style=\"text-align: right;\">{amounts['USD-PY']:,.2f}</td><td style=\"text-align: right;\">{amounts['PYG-PY']:,.2f}</td></tr>\n"
        )
    output.write("</table>")
    response = make_response(output.getvalue(), 200)
    response.mimetype = "text/html"
    return response


class AnalyticsView(BaseView):
    @expose("/")
    def index(self):
        return self.render("analytics_index.html")


admin.add_view(AnalyticsView(name="Analytics", endpoint="analytics"))

# import views after the app and globals have been defined so that the
# decorators in the view modules can register themselves without causing
# circular import errors.  Additional view modules should be imported here.
from views import \
    cash_flow as vcf  # noqa: F401 - import for side-effects to register routes
from views import investment_performance as vip
from views import upcoming_payments as vup  # noqa: F401 - import for side-effects to register routes


@app.route("/investment-performance")
def investment_performance():
    global ASSETS
    # ensure assets are loaded in the shared cache
    if not ASSETS:
        ASSETS = load_assets(fetch_assets, config.BASE_PATH, "key.json")
        append_cb(ASSETS)
    return vip.investment_performance(ASSETS)


@app.route("/cash-flow-detail")
def cash_flow():
    global ASSETS
    # ensure assets are loaded in the shared cache
    if not ASSETS:
        ASSETS = load_assets(fetch_assets, config.BASE_PATH, "key.json")
        append_cb(ASSETS)
    return vcf.cash_flow(ASSETS)

@app.route("/upcoming-payments")
def upcoming_payments():
    global ASSETS
    # ensure assets are loaded in the shared cache
    if not ASSETS:
        ASSETS = load_assets(fetch_assets, config.BASE_PATH, "key.json")
        append_cb(ASSETS)
    return vup.upcoming_payments(ASSETS)

if __name__ == "__main__":
    app.run()
