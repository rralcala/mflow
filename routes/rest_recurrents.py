from http import HTTPStatus

from flask import jsonify, request
from flask_login import current_user, login_required

from data.asset_store import reload_asset_store
from lib.config import Config
from lib.logger import get_logger
from lib.user_config import UserStore
from models.models import Recurrent, RecurrentTransaction

from .blueprints import assets_bp

Logger = get_logger()


@assets_bp.route("/recurrentTransactions", methods=["GET", "POST"])
@login_required
def recurrent_transactions():
    if request.method == "POST":
        data = request.json
        new_transaction = RecurrentTransaction(
            parent_id=data.get("recurrentId"),
            year_month=data.get("yearMonth"),
            description=data.get("description"),
            amount=data.get("amount"),
            transaction_date=data.get("transactionDate"),
            paid_with=data.get("paidWithAssetId"),
            user_id=int(current_user.id),
        )
        with Config.DB_SESSION() as session:
            session.add(new_transaction)
            session.commit()
            reload_asset_store(UserStore.get_user_config(current_user.id))
            return jsonify(new_transaction.to_dict()), 201
    else:

        with Config.DB_SESSION() as session:
            base_query = session.query(Recurrent).filter_by(
                user_id=int(current_user.id)
            )
            parent_recurrents = base_query.all()
            recurrents = {}
            for post in parent_recurrents:
                recurrents[post.identifier] = post.to_dict()

            base_query = session.query(RecurrentTransaction).filter(
                RecurrentTransaction.user_id == int(current_user.id)
            )
            if "recurrentId" in request.args:
                base_query = base_query.filter(
                    RecurrentTransaction.parent_id == request.args["recurrentId"],
                )
            if "yearMonth" in request.args:
                base_query = base_query.filter(
                    RecurrentTransaction.year_month == request.args["yearMonth"],
                )

            results = []
            for post in base_query.order_by(
                RecurrentTransaction.transaction_date.desc()
            ).all():
                record = post.to_dict()
                record["currency"] = recurrents.get(post.parent_id, {}).get(
                    "currency", ""
                )
                results.append(record)

        response = jsonify(results)
        response.headers["X-Total-Count"] = len(results)
    return response, HTTPStatus.OK


@assets_bp.route("/recurrentTransactions/<name>", methods=["GET", "PUT", "DELETE"])
@login_required
def recurrent_transactions_get(name):
    with Config.DB_SESSION() as session:
        result = (
            session.query(RecurrentTransaction)
            .filter_by(user_id=int(current_user.id), transaction_id=name)
            .first()
        )
        if result is None:
            return (
                jsonify({"message": "Recurrent Transaction not found"}),
                HTTPStatus.NOT_FOUND,
            )
        if request.method == "PUT":
            data = request.json
            result.year_month = data.get("yearMonth", result.year_month)
            result.paid_with = data.get("paidWithAssetId", result.paid_with)
            result.transaction_date = data.get(
                "transactionDate", result.transaction_date
            )
            result.parent_id = data.get("recurrentId", result.parent_id)
            result.amount = data.get("amount", result.amount)
            result.description = data.get("description", result.description)
            session.commit()
            reload_asset_store(UserStore.get_user_config(current_user.id))
        elif request.method == "DELETE":
            session.delete(result)
            session.commit()
            reload_asset_store(UserStore.get_user_config(current_user.id))
        return jsonify(result.to_dict()), HTTPStatus.OK


@assets_bp.route("/recurrents", methods=["GET", "POST"])
@login_required
def recurrents_all():
    if request.method == "POST":
        data = request.json
        new_transaction = Recurrent(
            identifier=data.get("id"),
            parent_asset_id=data.get("assetId"),
            country=data.get("country"),
            amount=data.get("amount"),
            currency=data.get("currency"),
            recurrence=data.get("recurrence"),
            start=data.get("start"),
            end=data.get("end"),
            flow_class=data.get("flowClass"),
            rate=data.get("rate"),
            user_id=int(current_user.id),
        )
        with Config.DB_SESSION() as session:
            session.add(new_transaction)
            session.commit()
            reload_asset_store(UserStore.get_user_config(current_user.id))
            return jsonify(new_transaction.to_dict()), 201
    else:
        with Config.DB_SESSION() as session:
            base_query = session.query(Recurrent).filter_by(
                user_id=int(current_user.id)
            )
            if "flowClass" in request.args:
                base_query = base_query.filter_by(flow_class=request.args["flowClass"])

            rows = base_query.all()

        results = sorted(
            [post.to_dict() for post in rows], key=lambda x: x.get("id", "")
        )
        response = jsonify(results)
        response.headers["X-Total-Count"] = len(results)
        return response, HTTPStatus.OK


@assets_bp.route("/recurrents/<name>", methods=["GET", "PUT", "DELETE"])
@login_required
def recurrents_get(name):
    with Config.DB_SESSION() as session:
        result = (
            session.query(Recurrent)
            .filter_by(user_id=int(current_user.id), identifier=name)
            .first()
        )
        if result is None:
            return jsonify({"message": "Recurrent not found"}), HTTPStatus.NOT_FOUND
        if request.method == "PUT":
            data = request.json
            result.parent_asset_id = data.get("assetId", result.parent_asset_id)
            result.country = data.get("country", result.country)
            result.amount = data.get("amount", result.amount)
            result.currency = data.get("currency", result.currency)
            result.recurrence = data.get("recurrence", result.recurrence)
            result.start = data.get("start", result.start)
            result.end = data.get("end", result.end)
            result.flow_class = data.get("flowClass", result.flow_class)
            result.rate = data.get("rate", result.rate)
            session.commit()
            reload_asset_store(UserStore.get_user_config(current_user.id))
        elif request.method == "DELETE":
            session.delete(result)
            session.commit()
            reload_asset_store(UserStore.get_user_config(current_user.id))
        return jsonify(result.to_dict()), HTTPStatus.OK
