from datetime import date
from http import HTTPStatus

from apiflask import APIBlueprint, abort
from flask import jsonify
from flask_login import current_user

from data.asset_store import get_asset_store
from data.exchange_rates import ExchangeRates
from lib.config import Config
from lib.logger import get_logger
from lib.user_config import UserStore
from lib.util import business_days_ago, paginate
from routes.schemas import (
    ExchangeRateOut,
    FutureTimelineQuery,
    MessageOut,
    MonthlyPnlQuery,
    RecurrentHistoryQuery,
    TotalCountHeader,
    UpcomingPaymentOut,
    UpcomingPaymentsQuery,
)
from routes.security import auth
from views import assets_by_location as vabl
from views import cash_flow as vcf
from views import future_timeline as vft
from views import history as vnh
from views import investment_performance as vip
from views import list_assets as vla
from views import monthly_pnl as vmpnl
from views import recurrent_history as vrh
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
@reports_bp.input(FutureTimelineQuery, location="query")
def future_timeline(query_data):
    """Monthly simulation of every asset until the user's LAST_UNTIL date."""
    try:
        user_config = UserStore.get_user_config(current_user.id)
        assets = get_asset_store(user_config)
        data = vft.future_timeline(
            assets,
            end_date=query_data.get("endDate") or user_config.LAST_UNTIL,
            inflation_rates=getattr(user_config, "INFLATION_RATES", None),
            include_capital_growth=query_data.get("capitalGrowth", False),
            desired_estate=float(getattr(user_config, "DESIRED_ESTATE", 0.0)),
        )
    except ValueError as exc:
        return jsonify({"message": str(exc)}), HTTPStatus.BAD_REQUEST

    response = jsonify(data)
    response.headers["X-Total-Count"] = len(data["months"])
    return response, HTTPStatus.OK


@reports_bp.route("/exchangeRatesRefresh", methods=["GET"])
@reports_bp.auth_required(auth)
@reports_bp.output(MessageOut)
def exchange_rates_refresh():
    try:
        ExchangeRates.refresh()
    except Exception as e:
        abort(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            f"Failed to refresh exchange rates: {str(e)}",
        )
    return {"message": "Exchange rates refreshed"}


@reports_bp.route("/exchangeRates", methods=["GET"])
@reports_bp.auth_required(auth)
@reports_bp.output(ExchangeRateOut(many=True), headers=TotalCountHeader)
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
    return result, HTTPStatus.OK, {"X-Total-Count": len(result)}


@reports_bp.route("/exchangeRates/<string:name>", methods=["GET"])
@reports_bp.auth_required(auth)
@reports_bp.output(ExchangeRateOut)
def exchange_rates_get(name):
    try:
        result = ExchangeRates.exchange_rate(name)
    except ValueError:
        abort(HTTPStatus.NOT_FOUND, "Exchange not found")

    return {"id": name, "rate": round(result, 2), "weekChange": round(result, 2)}


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
@reports_bp.input(MonthlyPnlQuery, location="query")
def monthly_pnl(query_data):
    skip_one_off = not query_data.get("oneOff", False)
    Logger.info(f"Calculating monthly P&L with skip_one_off={skip_one_off}")
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


@reports_bp.route("/recurrent_history", methods=["GET"])
@reports_bp.auth_required(auth)
@reports_bp.input(RecurrentHistoryQuery, location="query")
def recurrent_history(query_data):
    """Recorded transactions per recurrent and month, with statistics.

    The range defaults to the twelve months ending with the current one.
    """
    default_start, default_end = vrh.default_range(date.today())
    try:
        data = vrh.recurrent_history(
            int(current_user.id),
            query_data.get("startYearMonth") or default_start,
            query_data.get("endYearMonth") or default_end,
            flow_class=query_data.get("flowClass") or None,
        )
    except ValueError as exc:
        return jsonify({"message": str(exc)}), HTTPStatus.BAD_REQUEST

    response = jsonify(data)
    response.headers["X-Total-Count"] = len(data["recurrents"])
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
@reports_bp.input(UpcomingPaymentsQuery, location="query")
@reports_bp.output(UpcomingPaymentOut(many=True), headers=TotalCountHeader)
def upcoming_payments_flat(query_data):
    exclude_capital = query_data.get("exclude", True)
    user_config = UserStore.get_user_config(current_user.id)
    payments_by_month = vup.upcoming_payments_flat(
        get_asset_store(user_config), exclude_capital
    )
    count = len(payments_by_month)
    # Sort by Year-Month, Country, Date
    payments_by_month.sort(key=lambda x: (x["date"][:8], x["country"], x["date"]))
    return paginate(payments_by_month), HTTPStatus.OK, {"X-Total-Count": count}


@reports_bp.route("/valuation_history", methods=["GET"])
@reports_bp.auth_required(auth)
def valuation_history():
    data = vnh.nw_history()
    count = len(data)

    response = jsonify(data)
    response.headers["X-Total-Count"] = count
    return response, HTTPStatus.OK
