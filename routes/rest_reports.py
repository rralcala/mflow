import io
from datetime import date, datetime
from http import HTTPStatus

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from data.asset_store import get_asset_store, reload_asset_store
from data.exchange_rates import ExchangeRates
from lib.config import Config
from lib.logger import get_logger
from lib.user_config import UserStore
from lib.util import business_days_ago
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
from views.upload_statement import upload_statement

reports_bp = Blueprint("reports", __name__)

Logger = get_logger()


@reports_bp.route("/assets_by_location", methods=["GET"])
@login_required
def assets_by_location():
    user_config = UserStore.get_user_config(current_user.id)
    assets = get_asset_store(user_config)
    data = vabl.assets_by_location_data(assets)
    count = len(data)

    response = jsonify(data)
    response.headers["X-Total-Count"] = count
    return response, HTTPStatus.OK


@reports_bp.route("/cash_flow", methods=["GET"])
@login_required
def cash_flow():
    user_config = UserStore.get_user_config(current_user.id)
    assets = get_asset_store(user_config)
    data = vcf.cash_flow(assets)
    count = len(data)

    response = jsonify(data)
    response.headers["X-Total-Count"] = count
    return response, HTTPStatus.OK


@reports_bp.route("/future_timeline", methods=["GET"])
@login_required
def future_timeline():
    """Expose a chart-ready projection view for value, yield and expiration timelines.

    This keeps report projection logic under views as database-like projections and
    serves the result through REST for frontend consumers such as React-Admin.
    """

    def arg_bool(name: str, default: bool) -> bool:
        value = request.args.get(name)
        if value is None:
            return default
        return value.lower() in ("1", "true", "yes", "y")

    def arg_date(name: str):
        value = request.args.get(name)
        if not value:
            return None
        return datetime.strptime(value, "%Y-%m-%d").date()

    try:
        user_config = UserStore.get_user_config(current_user.id)
        assets = get_asset_store(user_config)
        data = vft.future_timeline(
            assets,
            mode=request.args.get("mode", "aggregated"),
            granularity=request.args.get("granularity", "monthly"),
            start_date=arg_date("startDate"),
            end_date=arg_date("endDate"),
            include_non_expiring_value=arg_bool("includeNonExpiringValue", True),
            include_expirations=arg_bool("includeExpirations", True),
            include_yield=arg_bool("includeYield", True),
            fallback_years=int(request.args.get("fallbackYears", 5)),
        )
    except ValueError as exc:
        return jsonify({"message": str(exc)}), HTTPStatus.BAD_REQUEST

    count = len(data)
    if "_start" in request.args and "_end" in request.args:
        start = int(request.args["_start"])
        end = int(request.args["_end"])
        data = data[start:end]

    response = jsonify(data)
    response.headers["X-Total-Count"] = count
    return response, HTTPStatus.OK


@reports_bp.route("/exchangeRatesRefresh", methods=["GET"])
@login_required
def exchange_rates_refresh():
    try:
        ExchangeRates._refresh_currency_data()
    except Exception as e:
        return (
            jsonify({"message": f"Failed to refresh exchange rates: {str(e)}"}),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )
    return jsonify({"message": "Exchange rates refreshed"}), HTTPStatus.OK


@reports_bp.route("/exchangeRates", methods=["GET"])
@login_required
def exchange_rates():
    user_config = UserStore.get_user_config(current_user.id)
    result = []
    selected_exchanges = f"USD{user_config.SECONDARY_CURRENCY}"
    for currency in user_config.TRADED_CRYPTO:
        selected_exchanges += f" {currency}USD"
    for currency in user_config.TRADED_STOCKS:
        selected_exchanges += f" {currency}"
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
@login_required
def exchange_rates_get(name):
    result = ExchangeRates.exchange_rate(name)
    if result is None:
        return jsonify({"message": "Exchange not found"}), HTTPStatus.NOT_FOUND

    return (
        jsonify({"id": name, "rate": round(result, 2), "weekChange": round(result, 2)}),
        HTTPStatus.OK,
    )


@reports_bp.route("/income_per_location", methods=["GET"])
@login_required
def income_per_location():
    user_config = UserStore.get_user_config(current_user.id)
    assets = get_asset_store(user_config)
    data = vla.list_income(assets)
    count = len(data)

    response = jsonify(data)
    response.headers["X-Total-Count"] = count
    return response, HTTPStatus.OK


@reports_bp.route("/investment_performance", methods=["GET"])
@login_required
def investment_performance():
    user_config = UserStore.get_user_config(current_user.id)
    assets = get_asset_store(user_config)
    data = vip.investment_performance(assets)
    count = len(data)

    response = jsonify(data)
    response.headers["X-Total-Count"] = count
    return response, HTTPStatus.OK


@reports_bp.route("/monthly_pnl", methods=["GET"])
@login_required
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
@login_required
def net_worth_summary():
    user_config = UserStore.get_user_config(current_user.id)
    assets = get_asset_store(user_config)
    data = vla.list_assets(assets)
    count = len(data)

    response = jsonify(data)
    response.headers["X-Total-Count"] = count
    return response, HTTPStatus.OK


@reports_bp.route("/projection_analysis", methods=["GET"])
@login_required
def projection_analysis():
    user_config = UserStore.get_user_config(current_user.id)
    assets = get_asset_store(user_config)
    data = vp.financial_analysis(assets)
    count = len(data)

    response = jsonify(data)
    response.headers["X-Total-Count"] = count
    return response, HTTPStatus.OK


@reports_bp.route("/spending_analysis", methods=["GET"])
@login_required
def spending_analysis():
    user_config = UserStore.get_user_config(current_user.id)
    assets = get_asset_store(user_config)
    data = vs.spending_analysis(assets)
    count = len(data)

    response = jsonify(data)
    response.headers["X-Total-Count"] = count
    return response, HTTPStatus.OK


@reports_bp.route("/upcoming_payments", methods=["GET"])
@login_required
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


@reports_bp.route("/upload-statement", methods=["POST"])
@login_required
def upload_statement_endpoint():
    if "statement" not in request.files:
        return jsonify({"message": "No file part"}), HTTPStatus.BAD_REQUEST
    update_balance = request.form.get("update", "0") == "1"
    account_id = request.form.get("account")
    file = request.files["statement"]
    if file.filename == "":
        return jsonify({"message": "No selected file"}), HTTPStatus.BAD_REQUEST

    in_memory_file = io.BytesIO(file.read())
    try:
        response, summary = upload_statement(
            Config.DB_SESSION(), update_balance, account_id, in_memory_file
        )
        if update_balance and account_id:
            reload_asset_store(UserStore.get_user_config(current_user.id))
    except ValueError as _:
        return (
            jsonify({"message": "Invalid file format. Required columns are missing."}),
            HTTPStatus.BAD_REQUEST,
        )
    except Exception as e:
        return (
            jsonify({"message": "An error occurred while processing the file."}),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )

    return jsonify({"message": response + summary}), HTTPStatus.OK


@reports_bp.route("/valuation_history", methods=["GET"])
@login_required
def valuation_history():
    user_config = UserStore.get_user_config(current_user.id)
    assets = get_asset_store(user_config)
    data = vnh.nw_history(assets)
    count = len(data)

    response = jsonify(data)
    response.headers["X-Total-Count"] = count
    return response, HTTPStatus.OK
