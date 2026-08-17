from http import HTTPStatus
from typing import Any, Dict, List

from flask import Response, jsonify, request
from flask_login import current_user, login_required

from data.asset_store import get_asset_store, reload_asset_store
from lib.config import Config
from lib.logger import get_logger
from lib.user_config import UserStore
from lib.util import error_response, validate_date
from models.instrument import Instrument
from models.models import Account
from models.payable import Payable
from models.property import Property
from reports.list_assets import asset_data_from_asset, get_assets
from reports.pnl import monthly_transactions as upcoming_monthly_transactions

from ..blueprints import assets_bp

Logger = get_logger()


@assets_bp.route("/accounts", methods=["GET", "POST"])
@login_required
def accounts():
    if request.method == "POST":
        with Config.DB_SESSION() as session:
            data = request.json
            new_transaction = Account(
                id=data.get("id"),
                country=data.get("country"),
                institution=data.get("institution"),
                currency=data.get("currency"),
                balance=data.get("balance"),
                factor=data.get("factor"),
                account_type=data.get("accountType"),
                liquid=1 if data.get("liquid") else 0,
                user_id=int(current_user.id),
            )
            session.add(new_transaction)
            session.commit()
            reload_asset_store(UserStore.get_user_config(current_user.id))
            return jsonify(new_transaction.to_dict()), 201
    else:
        with Config.DB_SESSION() as session:
            results = [
                post.to_dict()
                for post in session.query(Account)
                .filter_by(user_id=int(current_user.id))
                .all()
            ]
            count = len(results)
            if "_sort" in request.args:
                sort_key = request.args["_sort"]
                reverse = request.args.get("_order", "ASC") == "DESC"
                results.sort(key=lambda x: x.get(sort_key, ""), reverse=reverse)
            if "_start" in request.args and "_end" in request.args:
                start = int(request.args["_start"])
                end = int(request.args["_end"])
                results = results[start:end]
            response = jsonify(results)
        response.headers["X-Total-Count"] = count

        return response, HTTPStatus.OK


@assets_bp.route("/assets/<identifier:id>", methods=["GET"])
@login_required
def asset_get(id):
    Logger.info(f"Fetching asset with id: {id} for user: {current_user.id}")
    assets = get_asset_store(UserStore.get_user_config(current_user.id))

    for sub in assets.values():
        for asset in sub:
            if asset.identifier == id:
                return (
                    jsonify(asset_data_from_asset(asset)),
                    HTTPStatus.OK,
                )
    return jsonify({"message": "Asset not found"}), HTTPStatus.NOT_FOUND


@assets_bp.route("/assets", methods=["GET"])
@login_required
def assets():
    liquid_only = False
    if "liquid" in request.args:
        liquid_only = request.args.get("liquid", False) == "true"

    user_config = UserStore.get_user_config(current_user.id)
    results = get_assets(get_asset_store(user_config), liquid_only=liquid_only)

    if "id" in request.args:
        ids = set(request.args.getlist("id"))
        results = [r for r in results if r.get("id") in ids]
    count = len(results)

    if "_sort" in request.args:
        sort_key = request.args["_sort"]
        reverse = request.args.get("_order", "ASC") == "DESC"
        results.sort(key=lambda x: x.get(sort_key, ""), reverse=reverse)
    if "_start" in request.args and "_end" in request.args:
        start = int(request.args["_start"])
        end = int(request.args["_end"])
        results = results[start:end]
    response = jsonify(results)
    response.headers["X-Total-Count"] = count

    return response, HTTPStatus.OK


@assets_bp.route("/accounts/<identifier:name>", methods=["GET", "PUT", "DELETE"])
@login_required
def get_account(name):
    with Config.DB_SESSION() as session:
        result = (
            session.query(Account)
            .filter_by(user_id=int(current_user.id), id=name)
            .first()
        )
        if result is None:
            response = jsonify({"message": "Account not found"}), HTTPStatus.NOT_FOUND
        else:
            if request.method == "PUT":
                data = request.json
                result.country = data.get("country", result.country)
                result.institution = data.get("institution", result.institution)
                result.currency = data.get("currency", result.currency)
                result.balance = data.get("balance", result.balance)
                result.factor = data.get("factor", result.factor)
                result.account_type = data.get("accountType", result.account_type)
                result.liquid = 1 if data.get("liquid", result.liquid) else 0
                session.commit()
            elif request.method == "DELETE":
                session.delete(result)
                session.commit()
            reload_asset_store(UserStore.get_user_config(current_user.id))
            response = jsonify(result.to_dict()), HTTPStatus.OK
    return response


@assets_bp.route("/instruments", methods=["GET", "POST"])
@login_required
def instruments():
    if request.method == "POST":
        data = request.json
        acquisition_date = data.get("acquisition_date")
        if not validate_date(acquisition_date):
            return error_response(
                f"Invalid date '{acquisition_date}'", HTTPStatus.BAD_REQUEST
            )
        new_transaction = Instrument(
            country=data.get("country"),
            location=data.get("location"),
            symbol=data.get("symbol"),
            currency=data.get("currency"),
            factor=data.get("factor"),
            qty=data.get("qty"),
            dividend=data.get("dividend"),
            dividend_rate=data.get("dividend_rate"),
            user_id=int(current_user.id),
            acquisition_date=acquisition_date,
            acquisition_price=data.get("acquisition_price"),
            liquid=1 if data.get("liquid") else 0,
            capital_rate=data.get("capital_rate", 0.0),
        )
        with Config.DB_SESSION() as session:
            session.add(new_transaction)
            session.commit()
            reload_asset_store(UserStore.get_user_config(current_user.id))
            return jsonify(new_transaction.to_dict()), 201
    else:
        with Config.DB_SESSION() as session:
            results = [
                post.to_dict()
                for post in session.query(Instrument)
                .filter_by(user_id=int(current_user.id))
                .all()
            ]
        count = len(results)
        if "_sort" in request.args:
            if request.args["_sort"] == "id":
                sort_key = "location"
            else:
                sort_key = request.args["_sort"]
            reverse = request.args.get("_order", "ASC") == "DESC"
            results.sort(key=lambda x: x.get(sort_key, ""), reverse=reverse)
        if "_start" in request.args and "_end" in request.args:
            start = int(request.args["_start"])
            end = int(request.args["_end"])
            results = results[start:end]
        response = jsonify(results)
        response.headers["X-Total-Count"] = count

    return response, HTTPStatus.OK


@assets_bp.route("/instruments/<int:id>", methods=["GET", "PUT", "DELETE"])
@login_required
def instruments_get(id):
    with Config.DB_SESSION() as session:
        result = (
            session.query(Instrument)
            .filter_by(user_id=int(current_user.id), id=id)
            .first()
        )
        if result is None:
            return jsonify({"message": "Instrument not found"}), HTTPStatus.NOT_FOUND
        if request.method == "PUT":
            data = request.json
            acquisition_date = data.get("acquisition_date")
            if not validate_date(acquisition_date):
                return error_response(
                    f"Invalid date '{acquisition_date}'", HTTPStatus.BAD_REQUEST
                )
            result.id = data.get("id", result.id)
            result.user_id = data.get("user_id", result.user_id)
            result.country = data.get("country", result.country)
            result.location = data.get("location", result.location)
            result.symbol = data.get("symbol", result.symbol)
            result.factor = data.get("factor", result.factor)
            result.qty = data.get("qty", result.qty)
            result.dividend = data.get("dividend", result.dividend)
            result.dividend_rate = data.get("dividend_rate", result.dividend_rate)
            result.currency = data.get("currency", result.currency)
            result.acquisition_date = acquisition_date
            result.acquisition_price = data.get(
                "acquisition_price", result.acquisition_price
            )
            result.liquid = 1 if data.get("liquid", result.liquid) else 0
            result.capital_rate = data.get("capital_rate", result.capital_rate)
            session.commit()
            reload_asset_store(UserStore.get_user_config(current_user.id))
        elif request.method == "DELETE":
            session.delete(result)
            session.commit()
            reload_asset_store(UserStore.get_user_config(current_user.id))

        return jsonify(result.to_dict()), HTTPStatus.OK


def load_tx() -> List[Dict[str, Any]]:
    transactions = []
    user_config = UserStore.get_user_config(current_user.id)
    for month, month_transactions in upcoming_monthly_transactions(
        get_asset_store(user_config), months=2, balance=True
    ):
        for transaction in month_transactions:
            new_tx = {
                "id": transaction["id"],
                "assetId": transaction["assetId"],
                "amount": transaction["amount"],
                "currency": transaction["currency"],
                "yearMonth": month,
            }
            transactions.append(new_tx)

    return transactions


@assets_bp.route("/monthlyTransactions", methods=["GET"])
@login_required
def monthly_transactions() -> Response:
    response_items = []
    transactions = load_tx()
    for transaction in transactions:
        if transaction.get("amount", 0.0) < 0.0:
            response_items.append(transaction)
    response = jsonify(response_items)
    response.headers["X-Total-Count"] = len(response_items)
    response.status_code = HTTPStatus.OK
    return response


@assets_bp.route("/monthlyTransactions/<name>", methods=["GET"])
@login_required
def monthly_transactions_get(name) -> Response:
    response = None
    for transaction in load_tx():
        if transaction.get("id") == name:
            response = jsonify(transaction)
            response.status_code = HTTPStatus.OK
            break
    if not response:
        response = jsonify({"message": "Transaction not found"})
        response.status_code = HTTPStatus.NOT_FOUND
    return response


@assets_bp.route("/payables", methods=["GET", "POST"])
@login_required
def payables():
    if request.method == "POST":
        data = request.json
        currency = data.get("currency").upper()
        country = data.get("country").upper()
        if currency.lower() not in Config.CURRENCIES:
            return jsonify({"message": "Bad currency"}), HTTPStatus.BAD_REQUEST
        if country not in Config.COUNTRIES:
            return jsonify({"message": "Bad Country"}), HTTPStatus.BAD_REQUEST
        due_date = data.get("dueDate")
        if not validate_date(due_date):
            return error_response(f"Invalid date '{due_date}'", HTTPStatus.BAD_REQUEST)
        new_transaction = Payable(
            country=country,
            currency=currency,
            description=data.get("description"),
            amount=data.get("amount"),
            balance=data.get("balance"),
            due_date=due_date,
            commited=1 if data.get("paidWithAssetId") else 0,
            user_id=int(current_user.id),
            one_off=1 if data.get("oneOff") else 0,
            flow_class=data.get("flowClass").lower(),
        )
        with Config.DB_SESSION() as session:
            session.add(new_transaction)
            session.commit()
            reload_asset_store(UserStore.get_user_config(current_user.id))
            return jsonify(new_transaction.to_dict()), 201
    else:
        with Config.DB_SESSION() as session:
            base_query = session.query(Payable).filter_by(user_id=int(current_user.id))
            if "flowClass" in request.args:
                base_query = base_query.filter_by(flow_class=request.args["flowClass"])

            results = [post.to_dict() for post in base_query.all()]
        count = len(results)
        if "_sort" in request.args and request.args["_sort"] != "id":
            sort_key = request.args["_sort"]
        else:
            sort_key = "dueDate"
        reverse = request.args.get("_order", "ASC") == "DESC"
        results.sort(key=lambda x: x.get(sort_key, ""), reverse=reverse)
        if "_start" in request.args and "_end" in request.args:
            start = int(request.args["_start"])
            end = int(request.args["_end"])
            results = results[start:end]

        response = jsonify(results)
        response.headers["X-Total-Count"] = count

        return response, HTTPStatus.OK


@assets_bp.route("/payables/<int:id>", methods=["GET", "PUT", "DELETE"])
@login_required
def payables_get(id):
    with Config.DB_SESSION() as session:
        result = (
            session.query(Payable)
            .filter_by(user_id=int(current_user.id), id=id)
            .first()
        )
        if result is None:
            return jsonify({"message": "Payable not found"}), HTTPStatus.NOT_FOUND
        if request.method == "PUT":
            data = request.json
            result.country = data.get("country", result.country)
            result.currency = data.get("currency", result.currency)
            result.amount = data.get("amount", result.amount)
            result.balance = data.get("balance", result.balance)
            result.due_date = data.get("dueDate", result.due_date)
            result.description = data.get("description", result.description)
            result.commited = 1 if data.get("commited", result.commited) else 0
            result.one_off = 1 if data.get("oneOff", result.one_off) else 0
            result.flow_class = data.get("flowClass", result.flow_class).lower()
            session.commit()
            reload_asset_store(UserStore.get_user_config(current_user.id))
        elif request.method == "DELETE":
            session.delete(result)
            session.commit()
            reload_asset_store(UserStore.get_user_config(current_user.id))
        return jsonify(result.to_dict()), HTTPStatus.OK


@assets_bp.route("/properties", methods=["GET", "POST"])
@login_required
def properties():
    if request.method == "POST":
        data = request.json
        new_transaction = Property(
            user_id=int(current_user.id),
            country=data.get("country"),
            currency=data.get("currency"),
            property_name=data.get("propertyName"),
            purchase_price=data.get("purchasePrice"),
            purchase_date=data.get("purchaseDate"),
            current_price=data.get("currentPrice"),
            rent_price=data.get("rentPrice"),
            depreciation=data.get("depreciation"),
            additional_data=data.get("additionalData"),
            rent_currency=data.get("rentCurrency"),
        )
        with Config.DB_SESSION() as session:
            session.add(new_transaction)
            session.commit()
            reload_asset_store(UserStore.get_user_config(current_user.id))
            return jsonify(new_transaction.to_dict()), 201
    else:
        with Config.DB_SESSION() as session:
            base_query = session.query(Property).filter_by(user_id=int(current_user.id))

            results = [post.to_dict() for post in base_query.all()]
        count = len(results)
        if "_sort" in request.args:
            sort_key = request.args["_sort"]
        else:
            sort_key = "propertyName"
        reverse = request.args.get("_order", "ASC") == "DESC"
        results.sort(key=lambda x: x.get(sort_key, ""), reverse=reverse)
        if "_start" in request.args and "_end" in request.args:
            start = int(request.args["_start"])
            end = int(request.args["_end"])
            results = results[start:end]

        response = jsonify(results)
        response.headers["X-Total-Count"] = count

        return response, HTTPStatus.OK


@assets_bp.route("/properties/<int:id>", methods=["GET", "PUT", "DELETE"])
@login_required
def properties_get(id):
    with Config.DB_SESSION() as session:
        result = (
            session.query(Property)
            .filter_by(user_id=int(current_user.id), id=id)
            .first()
        )
        if result is None:
            return jsonify({"message": "Property not found"}), HTTPStatus.NOT_FOUND
        if request.method == "PUT":
            data = request.json
            result.country = data.get("country", result.country)
            result.currency = data.get("currency", result.currency)
            result.property_name = data.get("propertyName", result.property_name)
            result.purchase_price = data.get("purchasePrice", result.purchase_price)
            result.purchase_date = data.get("purchaseDate", result.purchase_date)
            result.current_price = data.get("currentPrice", result.current_price)
            result.rent_price = data.get("rentPrice", result.rent_price)
            result.depreciation = data.get("depreciation", result.depreciation)
            result.additional_data = data.get("additionalData", result.additional_data)
            result.rent_currency = data.get("rentCurrency", result.rent_currency)

            session.commit()
            reload_asset_store(UserStore.get_user_config(current_user.id))
        elif request.method == "DELETE":
            session.delete(result)
            session.commit()
            reload_asset_store(UserStore.get_user_config(current_user.id))
        return jsonify(result.to_dict()), HTTPStatus.OK


@assets_bp.route("/reload")
@login_required
def reload_assets():
    reload_asset_store(UserStore.get_user_config(current_user.id))

    return jsonify({"message": "Assets reloaded"}), HTTPStatus.OK
