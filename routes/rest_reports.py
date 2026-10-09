from datetime import date
from http import HTTPStatus

from apiflask import APIBlueprint
from flask import jsonify, request
from flask_login import current_user

from data.asset_store import get_asset_store
from data.exchange_rates import ExchangeRates
from lib.config import Config
from lib.logger import get_logger
from lib.user_config import UserStore
from lib.util import business_days_ago
from routes.security import auth
from views import assets_by_location as vabl
from views import cash_flow as vcf
from views import future_timeline as vft
from views import history as vnh
from views import investment_performance as vip
from views import list_assets as vla
from views import monthly_pnl as vmpnl
from views import projection as vp
from views import spending as vs
from views import upcoming_payments as vup

reports_bp = APIBlueprint("reports", __name__, tag="reports")

Logger = get_logger()


@reports_bp.route("/assets_by_location", methods=["GET"])
@reports_bp.auth_required(auth)
def assets_by_location():
    user_config = UserStore.get_user_config(current_user.id)
    assets = get_asset_store(user_config)
    data = vabl.assets_by_location_data(assets)
    count = len(data)

    response = jsonify(data)
    response.headers["X-Total-Count"] = count
    return response, HTTPStatus.OK


@reports_bp.route("/cash_flow", methods=["GET"])
@reports_bp.auth_required(auth)
def cash_flow():
    user_config = UserStore.get_user_config(current_user.id)
    assets = get_asset_store(user_config)
    data = vcf.cash_flow(assets)
    count = len(data)

    response = jsonify(data)
    response.headers["X-Total-Count"] = count
    return response, HTTPStatus.OK


@reports_bp.route("/future_timeline", methods=["GET"])
@reports_bp.auth_required(auth)
def future_timeline():
    """Monthly simulation of every asset until the user's LAST_UNTIL date.

    Optional query args: endDate (YYYY-MM-DD, defaults to LAST_UNTIL) and
    capitalGrowth (0/1, whether instruments appreciate by their capital rate).
    """
    try:
        user_config = UserStore.get_user_config(current_user.id)
        assets = get_asset_store(user_config)
        data = vft.future_timeline(
            assets,
            end_date=request.args.get("endDate") or user_config.LAST_UNTIL,
            inflation_rates=getattr(user_config, "INFLATION_RATES", None),
            include_capital_growth=request.args.get("capitalGrowth", "0") == "1",
            desired_estate=float(getattr(user_config, "DESIRED_ESTATE", 0.0)),
        )
    except ValueError as exc:
        return jsonify({"message": str(exc)}), HTTPStatus.BAD_REQUEST

    response = jsonify(data)
    response.headers["X-Total-Count"] = len(data["months"])
    return response, HTTPStatus.OK


@reports_bp.route("/exchangeRatesRefresh", methods=["GET"])
@reports_bp.auth_required(auth)
def exchange_rates_refresh():
    try:
        ExchangeRates.refresh()
    except Exception as e:
        return (
            jsonify({"message": f"Failed to refresh exchange rates: {str(e)}"}),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )
    return jsonify({"message": "Exchange rates refreshed"}), HTTPStatus.OK


@reports_bp.route("/exchangeRates", methods=["GET"])
@reports_bp.auth_required(auth)
def exchange_rates():
    user_config = UserStore.get_user_config(current_user.id)
    result = []
    selected_exchanges = f"USD{user_config.SECONDARY_CURRENCY}"
    for currency in Config.TRADED_CRYPTO:
        selected_exchanges += f" {currency}USD"
    for stock in Config.TRADED_STOCKS:
        selected_exchanges += f" {stock}"
    for metal in Config.TRADED_METALS:
        selected_exchanges += f" {metal}"
    for key, value in ExchangeRates.get_all().items():
        if key in selected_exchanges.split():
            result.append({"id": key, "rate": value, "weekChange": value})
    previous = ExchangeRates.local_quotes_on(
        business_days_ago(5, date.today()).strftime("%Y-%m-%d")
    )
    previous_dict = {symbol: rate for symbol, rate in previous}
    for item in result:
        item["weekChange"] = previous_dict.get(item["id"], item["rate"])
        item["weekChange"] = (item["rate"] / item["weekChange"]) - 1

    result = sorted(result, key=lambda x: x["id"])
    response = jsonify(result)
    response.headers["X-Total-Count"] = len(result)
    return response, HTTPStatus.OK


@reports_bp.route("/exchangeRates/<string:name>", methods=["GET"])
@reports_bp.auth_required(auth)
def exchange_rates_get(name):
    try:
        result = ExchangeRates.exchange_rate(name)
    except ValueError:
        return jsonify({"message": "Exchange not found"}), HTTPStatus.NOT_FOUND

    return (
        jsonify({"id": name, "rate": round(result, 2), "weekChange": round(result, 2)}),
        HTTPStatus.OK,
    )


@reports_bp.route("/income_per_location", methods=["GET"])
@reports_bp.auth_required(auth)
def income_per_location():
    user_config = UserStore.get_user_config(current_user.id)
    assets = get_asset_store(user_config)
    data = vla.list_income(assets)
    count = len(data)

    response = jsonify(data)
    response.headers["X-Total-Count"] = count
    return response, HTTPStatus.OK


@reports_bp.route("/investment_performance", methods=["GET"])
@reports_bp.auth_required(auth)
def investment_performance():
    user_config = UserStore.get_user_config(current_user.id)
    assets = get_asset_store(user_config)
    data = vip.investment_performance(assets)
    count = len(data)

    response = jsonify(data)
    response.headers["X-Total-Count"] = count
    return response, HTTPStatus.OK


@reports_bp.route("/monthly_pnl", methods=["GET"])
@reports_bp.auth_required(auth)
def monthly_pnl():
    skip_one_off = request.args.get("oneOff", "0") == "0"
    Logger.info(
        f"Calculating monthly P&L with skip_one_off={skip_one_off} {request.args.get('oneOff', '1')}"
    )
    assets = get_asset_store(UserStore.get_user_config(current_user.id))
    year_months, summary = vmpnl.monthly_pnl(assets, skip_one_off=skip_one_off)
    response = jsonify({"year_months": year_months, "summary": summary})
    response.headers["X-Total-Count"] = len(year_months)
    return response, HTTPStatus.OK


@reports_bp.route("/nw_summary", methods=["GET"])
@reports_bp.auth_required(auth)
def net_worth_summary():
    user_config = UserStore.get_user_config(current_user.id)
    assets = get_asset_store(user_config)
    data = vla.list_assets(assets)
    count = len(data)

    response = jsonify(data)
    response.headers["X-Total-Count"] = count
    return response, HTTPStatus.OK


@reports_bp.route("/projection_analysis", methods=["GET"])
@reports_bp.auth_required(auth)
def projection_analysis():
    user_config = UserStore.get_user_config(current_user.id)
    assets = get_asset_store(user_config)
    data = vp.financial_analysis(assets)
    count = len(data)

    response = jsonify(data)
    response.headers["X-Total-Count"] = count
    return response, HTTPStatus.OK


@reports_bp.route("/spending_analysis", methods=["GET"])
@reports_bp.auth_required(auth)
def spending_analysis():
    user_config = UserStore.get_user_config(current_user.id)
    assets = get_asset_store(user_config)
    data = vs.spending_analysis(assets)
    count = len(data)

    response = jsonify(data)
    response.headers["X-Total-Count"] = count
    return response, HTTPStatus.OK


@reports_bp.route("/upcoming_payments", methods=["GET"])
@reports_bp.auth_required(auth)
def upcoming_payments_flat():
    exclude_capital = request.args.get("exclude", "1") == "1"
    user_config = UserStore.get_user_config(current_user.id)
    payments_by_month = vup.upcoming_payments_flat(
        get_asset_store(user_config), exclude_capital
    )
    count = len(payments_by_month)
    # Sort by Year-Month, Country, Date
    payments_by_month.sort(key=lambda x: (x["date"][:8], x["country"], x["date"]))
    if "_start" in request.args and "_end" in request.args:
        start = int(request.args["_start"])
        end = int(request.args["_end"])
        payments_by_month = payments_by_month[start:end]
    response = jsonify(payments_by_month)
    response.headers["X-Total-Count"] = count
    return response, HTTPStatus.OK


@reports_bp.route("/valuation_history", methods=["GET"])
@reports_bp.auth_required(auth)
def valuation_history():
    data = vnh.nw_history()
    count = len(data)

    response = jsonify(data)
    response.headers["X-Total-Count"] = count
    return response, HTTPStatus.OK
