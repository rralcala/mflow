import csv
from http import HTTPStatus
from io import StringIO

from flask import Response, jsonify, request
from flask_login import current_user, login_required

from data.asset_store import reload_asset_store
from lib.config import Config
from lib.user_config import UserStore
from lib.util import type_to_str
from models.bond import Bond, BondSchedule
from models.deposit_certificate import DepositCertificate, DepositCertificateSchedule

from ..blueprints import assets_bp


@assets_bp.route("/bondSchedulesUpload", methods=["POST"])
@login_required
def bond_schedules_upload():
    f = StringIO(request.data.decode("utf-8"))
    reader = csv.DictReader(f)
    with Config.DB_SESSION() as session:
        c = 0
        for row in reader:
            new_item = BondSchedule(
                bond_id=int(row["iid"]),
                date=row["date"],
                user_id=int(current_user.id),
                amount=str(float(row["amount"])),
                paid=1 if row["paid"] == "1" else 0,
            )

            session.add(new_item)
            c += 1
        session.commit()
    response = jsonify({"message": f"inserted: {c}"}), HTTPStatus.CREATED
    return response


@assets_bp.route("/bondSchedules", methods=["GET", "POST"])
@login_required
def bond_schedules_all():
    print(Config.__dict__)
    if request.method == "POST":
        data = request.json
        with Config.DB_SESSION() as session:
            new_item = BondSchedule(
                bond_id=data.get("bondId"),
                date=data.get("transactionDate"),
                user_id=int(current_user.id),
                amount=data.get("amount"),
                paid=1 if data.get("paid", False) else 0,
            )

            session.add(new_item)
            session.commit()
            response = jsonify(new_item.to_dict()), HTTPStatus.CREATED
            reload_asset_store(UserStore.get_user_config(current_user.id))
        return response
    else:
        with Config.DB_SESSION() as session:
            base_query = session.query(BondSchedule).filter(
                BondSchedule.user_id == int(current_user.id)
            )
            if "bondId" in request.args:
                base_query = base_query.filter(
                    BondSchedule.bond_id == request.args["bondId"]
                )
            if "paid" in request.args:
                paid_value = request.args["paid"].lower() == "true"
                base_query = base_query.filter(
                    BondSchedule.paid == (1 if paid_value else 0)
                )
            results = [
                post.to_dict()
                for post in base_query.order_by(BondSchedule.date.asc()).all()
            ]
            response = jsonify(results)

        response.headers["X-Total-Count"] = len(results)
        return response, HTTPStatus.OK


@assets_bp.route("/bondSchedules/<id>", methods=["GET", "PUT"])
@login_required
def bond_schedules_get(id):
    with Config.DB_SESSION() as session:
        result = (
            session.query(BondSchedule)
            .filter_by(user_id=int(current_user.id), id=id)
            .first()
        )
        if result is None:
            return jsonify({"message": "Bond Schedule not found"}), HTTPStatus.NOT_FOUND
        if request.method == "PUT":
            data = request.json
            result.date = data.get("transactionDate", result.date)
            result.amount = data.get("amount", result.amount)
            result.paid = 1 if data.get("paid", result.paid == 1) else 0
            session.commit()
            reload_asset_store(UserStore.get_user_config(current_user.id))
        return jsonify(result.to_dict()), HTTPStatus.OK


@assets_bp.route("/depositCertificateSchedules", methods=["GET", "POST"])
@login_required
def deposit_certificate_schedules_all():
    if request.method == "POST":
        data = request.json
        with Config.DB_SESSION() as session:
            new_item = DepositCertificateSchedule(
                cd_id=data.get("cdId"),
                date=data.get("transactionDate"),
                user_id=int(current_user.id),
                amount=data.get("amount"),
                paid=1 if data.get("paid", False) else 0,
            )

            session.add(new_item)
            session.commit()
            reload_asset_store(UserStore.get_user_config(current_user.id))
            return jsonify(new_item.to_dict()), HTTPStatus.CREATED
    else:
        with Config.DB_SESSION() as session:
            base_query = session.query(DepositCertificateSchedule).filter(
                DepositCertificateSchedule.user_id == int(current_user.id)
            )
            if "depositCertificateId" in request.args:
                base_query = base_query.filter(
                    DepositCertificateSchedule.cd_id
                    == request.args["depositCertificateId"]
                )
            if "paid" in request.args:
                paid_value = request.args["paid"].lower() == "true"
                base_query = base_query.filter(
                    DepositCertificateSchedule.paid == (1 if paid_value else 0)
                )
            results = [
                post.to_dict()
                for post in base_query.order_by(
                    DepositCertificateSchedule.date.asc()
                ).all()
            ]

            response = jsonify(results)
        response.headers["X-Total-Count"] = len(results)
        return response, HTTPStatus.OK


@assets_bp.route("/depositCertificateSchedules/<id>", methods=["GET", "PUT"])
@login_required
def deposit_certificate_schedules_get(id):
    with Config.DB_SESSION() as session:
        result = (
            session.query(DepositCertificateSchedule)
            .filter_by(user_id=int(current_user.id), id=id)
            .first()
        )
        if result is None:
            return (
                jsonify({"message": "Deposit Certificate Schedule not found"}),
                HTTPStatus.NOT_FOUND,
            )
        if request.method == "PUT":
            data = request.json
            result.date = data.get("transactionDate", result.date)
            result.amount = data.get("amount", result.amount)
            result.paid = 1 if data.get("paid", result.paid == 1) else 0
            session.commit()
            reload_asset_store(UserStore.get_user_config(current_user.id))
        return jsonify(result.to_dict()), HTTPStatus.OK


@assets_bp.route("/bonds/<id>", methods=["GET", "PUT", "DELETE"])
@login_required
def bonds_get(id):
    return certificate_get(Bond, request, id)


@assets_bp.route("/depositCertificates/<int:id>", methods=["GET", "PUT", "DELETE"])
@login_required
def deposit_certificates_get(id):
    return certificate_get(DepositCertificate, request, id)


def certificate_get(cert_type, request_input, id):
    with Config.DB_SESSION() as session:
        result = (
            session.query(cert_type)
            .filter_by(user_id=int(current_user.id), id=id)
            .first()
        )
        if result is None:
            return (
                jsonify({"message": f"{type_to_str(cert_type)} not found"}),
                HTTPStatus.NOT_FOUND,
            )
        elif request_input.method == "PUT":
            data = request_input.json
            result.name = data.get("name", result.name)
            result.capital = data.get("capital", result.capital)
            result.rate = data.get("rate", result.rate)
            result.maturity_date = data.get("maturityDate", result.maturity_date)
            result.currency = data.get("currency", result.currency)
            result.entity = data.get("entity", result.entity)
            result.country = data.get("country", result.country)
            session.commit()
            reload_asset_store(UserStore.get_user_config(current_user.id))
        elif request_input.method == "DELETE":
            session.delete(result)
            session.commit()
        reload_asset_store(UserStore.get_user_config(current_user.id))
        response = jsonify(result.to_dict()), HTTPStatus.OK
    return response


@assets_bp.route("/bonds", methods=["GET", "POST"])
@login_required
def bonds_all():
    return certificates_all(request, Bond)


@assets_bp.route("/depositCertificates", methods=["GET", "POST"])
@login_required
def deposit_certificates_all():
    return certificates_all(request, DepositCertificate)


def certificates_all(request_input, cert_type) -> tuple[Response, HTTPStatus]:
    if request_input.method == "POST":
        data = request_input.json
        currency = data.get("currency").upper()
        country = data.get("country").upper()
        if currency.lower() not in Config.CURRENCIES:
            return jsonify({"message": "Bad currency"}), HTTPStatus.BAD_REQUEST
        if country not in Config.COUNTRIES:
            return jsonify({"message": "Bad Country"}), HTTPStatus.BAD_REQUEST
        with Config.DB_SESSION() as session:
            new_item = cert_type(
                name=data.get("name"),
                capital=data.get("capital"),
                rate=data.get("rate"),
                maturity_date=data.get("maturityDate"),
                currency=currency,
                entity=data.get("entity"),
                country=country,
                user_id=int(current_user.id),
                purchase_price=data.get("capital"),
            )

            session.add(new_item)
            session.commit()
            reload_asset_store(UserStore.get_user_config(current_user.id))
            response = jsonify(new_item.to_dict())
        return response, HTTPStatus.CREATED
    else:
        with Config.DB_SESSION() as session:
            rows = session.query(cert_type).filter_by(user_id=int(current_user.id))
            sort_key = "name"
            if "_sort" in request_input.args:
                if request_input.args["_sort"] != "id":
                    sort_key = request_input.args["_sort"]
            if sort_key == "maturityDate":
                if request_input.args.get("_order", "ASC") == "DESC":
                    rows = rows.order_by(cert_type.maturity_date.desc())
                else:
                    rows = rows.order_by(cert_type.maturity_date.asc())
            if sort_key == "name":
                if request_input.args.get("_order", "ASC") == "DESC":
                    rows = rows.order_by(cert_type.name.desc())
                else:
                    rows = rows.order_by(cert_type.name.asc())
            results = [post.to_dict() for post in rows.all()]
            response = jsonify(results)

        response.headers["X-Total-Count"] = len(results)
        return response, HTTPStatus.OK
