import csv
from http import HTTPStatus
from io import StringIO

from apiflask import abort
from flask import request
from flask_login import current_user

from data.asset_store import reload_asset_store
from lib.config import Config
from lib.user_config import UserStore
from lib.util import (
    country_for_update,
    normalize_country,
    normalize_currency,
    owned_or_404,
    paginate,
    require_date,
    require_number,
    type_to_str,
    validate_target_asset,
)
from models.bond import Bond, BondSchedule
from models.deposit_certificate import DepositCertificate, DepositCertificateSchedule

from ..blueprints import assets_bp
from ..schemas import (
    BondIn,
    BondOut,
    BondScheduleIn,
    BondScheduleOut,
    BondScheduleQuery,
    DepositCertificateIn,
    DepositCertificateOut,
    DepositCertificateScheduleIn,
    DepositCertificateScheduleOut,
    DepositCertificateScheduleQuery,
    ListQuery,
    MessageOut,
    TotalCountHeader,
)
from ..security import auth


@assets_bp.post("/cdSchedulesUpload")
@assets_bp.auth_required(auth)
@assets_bp.output(MessageOut, status_code=HTTPStatus.CREATED)
def cd_schedules_upload():
    """Upload deposit certificate schedule rows.

    The body is CSV text with the header `iid,date,amount,paid`, where `iid` is
    the deposit certificate id and `paid` is 1 or 0.
    """
    f = StringIO(request.data.decode("utf-8"))
    reader = csv.DictReader(f)
    with Config.DB_SESSION() as session:
        c = 0
        for row in reader:
            new_item = DepositCertificateSchedule(
                cd_id=int(row["iid"]),
                date=require_date(row["date"], "date"),
                user_id=int(current_user.id),
                amount=require_number(row.get("amount"), "amount"),
                paid=1 if row["paid"] == "1" else 0,
            )

            session.add(new_item)
            c += 1
        session.commit()
    return {"message": f"inserted: {c}"}


@assets_bp.post("/bondSchedulesUpload")
@assets_bp.auth_required(auth)
@assets_bp.output(MessageOut, status_code=HTTPStatus.CREATED)
def bond_schedules_upload():
    """Upload bond schedule rows.

    The body is CSV text with the header `iid,date,amount,paid`, where `iid` is
    the bond id and `paid` is 1 or 0.
    """
    f = StringIO(request.data.decode("utf-8"))
    reader = csv.DictReader(f)
    with Config.DB_SESSION() as session:
        c = 0
        for row in reader:
            new_item = BondSchedule(
                bond_id=int(row["iid"]),
                date=require_date(row["date"], "date"),
                user_id=int(current_user.id),
                amount=require_number(row.get("amount"), "amount"),
                paid=1 if row["paid"] == "1" else 0,
            )

            session.add(new_item)
            c += 1
        session.commit()
    return {"message": f"inserted: {c}"}


@assets_bp.get("/bondSchedules")
@assets_bp.auth_required(auth)
@assets_bp.input(BondScheduleQuery, location="query")
@assets_bp.output(BondScheduleOut(many=True), headers=TotalCountHeader)
def bond_schedules_list(query_data):
    with Config.DB_SESSION() as session:
        base_query = session.query(BondSchedule).filter(
            BondSchedule.user_id == int(current_user.id)
        )
        if "bondId" in query_data:
            base_query = base_query.filter(BondSchedule.bond_id == query_data["bondId"])
        if "paid" in query_data:
            base_query = base_query.filter(
                BondSchedule.paid == (1 if query_data["paid"] else 0)
            )
        results = [
            post.to_dict()
            for post in base_query.order_by(BondSchedule.date.asc()).all()
        ]
    count = len(results)
    return paginate(results), HTTPStatus.OK, {"X-Total-Count": count}


@assets_bp.post("/bondSchedules")
@assets_bp.auth_required(auth)
@assets_bp.input(BondScheduleIn)
@assets_bp.output(BondScheduleOut, status_code=HTTPStatus.CREATED)
def bond_schedule_create(json_data):
    data = json_data
    with Config.DB_SESSION() as session:
        new_item = BondSchedule(
            bond_id=data.get("bondId"),
            date=require_date(data.get("transactionDate"), "transactionDate"),
            user_id=int(current_user.id),
            amount=require_number(data.get("amount"), "amount"),
            paid=1 if data.get("paid", False) else 0,
        )

        session.add(new_item)
        session.commit()
        reload_asset_store(UserStore.get_user_config(current_user.id))
        return new_item.to_dict()


@assets_bp.get("/bondSchedules/<id>")
@assets_bp.auth_required(auth)
@assets_bp.output(BondScheduleOut)
def bond_schedule_get(id):
    with Config.DB_SESSION() as session:
        return find_bond_schedule(session, id).to_dict()


@assets_bp.put("/bondSchedules/<id>")
@assets_bp.auth_required(auth)
@assets_bp.input(BondScheduleIn(partial=True, exclude=("bondId",)))
@assets_bp.output(BondScheduleOut)
def bond_schedule_update(id, json_data):
    with Config.DB_SESSION() as session:
        result = find_bond_schedule(session, id)
        update_schedule(result, json_data)
        session.commit()
        reload_asset_store(UserStore.get_user_config(current_user.id))
        return result.to_dict()


def find_bond_schedule(session, id) -> BondSchedule:
    return owned_or_404(
        session, BondSchedule, int(current_user.id), "Bond Schedule not found", id=id
    )


def update_schedule(result, data) -> None:
    result.date = require_date(
        data.get("transactionDate", result.date), "transactionDate"
    )
    result.amount = require_number(data.get("amount", result.amount), "amount")
    result.paid = 1 if data.get("paid", result.paid == 1) else 0


@assets_bp.get("/depositCertificateSchedules")
@assets_bp.auth_required(auth)
@assets_bp.input(DepositCertificateScheduleQuery, location="query")
@assets_bp.output(DepositCertificateScheduleOut(many=True), headers=TotalCountHeader)
def deposit_certificate_schedules_list(query_data):
    with Config.DB_SESSION() as session:
        base_query = session.query(DepositCertificateSchedule).filter(
            DepositCertificateSchedule.user_id == int(current_user.id)
        )
        if "depositCertificateId" in query_data:
            base_query = base_query.filter(
                DepositCertificateSchedule.cd_id == query_data["depositCertificateId"]
            )
        if "paid" in query_data:
            base_query = base_query.filter(
                DepositCertificateSchedule.paid == (1 if query_data["paid"] else 0)
            )
        results = [
            post.to_dict()
            for post in base_query.order_by(DepositCertificateSchedule.date.asc()).all()
        ]
    count = len(results)
    return paginate(results), HTTPStatus.OK, {"X-Total-Count": count}


@assets_bp.post("/depositCertificateSchedules")
@assets_bp.auth_required(auth)
@assets_bp.input(DepositCertificateScheduleIn)
@assets_bp.output(DepositCertificateScheduleOut, status_code=HTTPStatus.CREATED)
def deposit_certificate_schedule_create(json_data):
    data = json_data
    with Config.DB_SESSION() as session:
        new_item = DepositCertificateSchedule(
            cd_id=data.get("cdId"),
            date=require_date(data.get("transactionDate"), "transactionDate"),
            user_id=int(current_user.id),
            amount=require_number(data.get("amount"), "amount"),
            paid=1 if data.get("paid", False) else 0,
        )

        session.add(new_item)
        session.commit()
        reload_asset_store(UserStore.get_user_config(current_user.id))
        return new_item.to_dict()


@assets_bp.get("/depositCertificateSchedules/<id>")
@assets_bp.auth_required(auth)
@assets_bp.output(DepositCertificateScheduleOut)
def deposit_certificate_schedule_get(id):
    with Config.DB_SESSION() as session:
        return find_deposit_certificate_schedule(session, id).to_dict()


@assets_bp.put("/depositCertificateSchedules/<id>")
@assets_bp.auth_required(auth)
@assets_bp.input(DepositCertificateScheduleIn(partial=True, exclude=("cdId",)))
@assets_bp.output(DepositCertificateScheduleOut)
def deposit_certificate_schedule_update(id, json_data):
    with Config.DB_SESSION() as session:
        result = find_deposit_certificate_schedule(session, id)
        update_schedule(result, json_data)
        session.commit()
        reload_asset_store(UserStore.get_user_config(current_user.id))
        return result.to_dict()


def find_deposit_certificate_schedule(session, id) -> DepositCertificateSchedule:
    return owned_or_404(
        session,
        DepositCertificateSchedule,
        int(current_user.id),
        "Deposit Certificate Schedule not found",
        id=id,
    )


@assets_bp.get("/bonds")
@assets_bp.auth_required(auth)
@assets_bp.input(ListQuery, location="query")
@assets_bp.output(BondOut(many=True), headers=TotalCountHeader)
def bonds_list(query_data):
    return certificates_list(Bond, query_data)


@assets_bp.post("/bonds")
@assets_bp.auth_required(auth)
@assets_bp.input(BondIn)
@assets_bp.output(BondOut, status_code=HTTPStatus.CREATED)
def bond_create(json_data):
    return certificate_create(Bond, json_data)


@assets_bp.get("/bonds/<id>")
@assets_bp.auth_required(auth)
@assets_bp.output(BondOut)
def bond_get(id):
    with Config.DB_SESSION() as session:
        return find_certificate(session, Bond, id).to_dict()


@assets_bp.put("/bonds/<id>")
@assets_bp.auth_required(auth)
@assets_bp.input(BondIn(partial=True))
@assets_bp.output(BondOut)
def bond_update(id, json_data):
    return certificate_update(Bond, id, json_data)


@assets_bp.delete("/bonds/<id>")
@assets_bp.auth_required(auth)
@assets_bp.output(BondOut)
def bond_delete(id):
    return certificate_delete(Bond, id)


@assets_bp.get("/depositCertificates")
@assets_bp.auth_required(auth)
@assets_bp.input(ListQuery, location="query")
@assets_bp.output(DepositCertificateOut(many=True), headers=TotalCountHeader)
def deposit_certificates_list(query_data):
    return certificates_list(DepositCertificate, query_data)


@assets_bp.post("/depositCertificates")
@assets_bp.auth_required(auth)
@assets_bp.input(DepositCertificateIn)
@assets_bp.output(DepositCertificateOut, status_code=HTTPStatus.CREATED)
def deposit_certificate_create(json_data):
    return certificate_create(DepositCertificate, json_data)


@assets_bp.get("/depositCertificates/<int:id>")
@assets_bp.auth_required(auth)
@assets_bp.output(DepositCertificateOut)
def deposit_certificate_get(id):
    with Config.DB_SESSION() as session:
        return find_certificate(session, DepositCertificate, id).to_dict()


@assets_bp.put("/depositCertificates/<int:id>")
@assets_bp.auth_required(auth)
@assets_bp.input(DepositCertificateIn(partial=True))
@assets_bp.output(DepositCertificateOut)
def deposit_certificate_update(id, json_data):
    return certificate_update(DepositCertificate, id, json_data)


@assets_bp.delete("/depositCertificates/<int:id>")
@assets_bp.auth_required(auth)
@assets_bp.output(DepositCertificateOut)
def deposit_certificate_delete(id):
    return certificate_delete(DepositCertificate, id)


def find_certificate(session, cert_type, id):
    return owned_or_404(
        session,
        cert_type,
        int(current_user.id),
        f"{type_to_str(cert_type)} not found",
        id=id,
    )


def certificate_update(cert_type, id, data):
    with Config.DB_SESSION() as session:
        result = find_certificate(session, cert_type, id)
        target_asset_id = data.get("targetAssetId", result.target_asset_id)
        currency = normalize_currency(data.get("currency", result.currency))
        maturity_date = require_date(
            data.get("maturityDate", result.maturity_date), "maturityDate"
        )
        capital = require_number(data.get("capital", result.capital), "capital")
        rate = require_number(data.get("rate", result.rate), "rate")
        if not validate_target_asset(
            session, int(current_user.id), target_asset_id, currency
        ):
            abort(HTTPStatus.BAD_REQUEST, "Bad target asset")
        result.name = data.get("name", result.name)
        result.capital = capital
        result.rate = rate
        result.maturity_date = maturity_date
        result.currency = currency
        result.entity = data.get("entity", result.entity)
        result.country = country_for_update(data, result.country)
        result.target_asset_id = target_asset_id
        session.commit()
        reload_asset_store(UserStore.get_user_config(current_user.id))
        return result.to_dict()


def certificate_delete(cert_type, id):
    with Config.DB_SESSION() as session:
        result = find_certificate(session, cert_type, id)
        session.delete(result)
        session.commit()
        reload_asset_store(UserStore.get_user_config(current_user.id))
        return result.to_dict()


def certificate_create(cert_type, data):
    currency = normalize_currency(data.get("currency"))
    country = normalize_country(data.get("country"))
    maturity_date = require_date(data.get("maturityDate"), "maturityDate")
    capital = require_number(data.get("capital"), "capital")
    rate = require_number(data.get("rate"), "rate")
    target_asset_id = data.get("targetAssetId")
    with Config.DB_SESSION() as session:
        if not validate_target_asset(
            session, int(current_user.id), target_asset_id, currency
        ):
            abort(HTTPStatus.BAD_REQUEST, "Bad target asset")
        new_item = cert_type(
            name=data.get("name"),
            capital=capital,
            rate=rate,
            maturity_date=maturity_date,
            currency=currency,
            entity=data.get("entity"),
            country=country,
            user_id=int(current_user.id),
            purchase_price=capital,
            target_asset_id=target_asset_id,
        )

        session.add(new_item)
        session.commit()
        reload_asset_store(UserStore.get_user_config(current_user.id))
        return new_item.to_dict()


def certificates_list(cert_type, query_data):
    with Config.DB_SESSION() as session:
        rows = session.query(cert_type).filter_by(user_id=int(current_user.id))
        sort_key = "name"
        if query_data.get("sort", "id") != "id":
            sort_key = query_data["sort"]
        descending = query_data.get("order", "ASC") == "DESC"
        if sort_key == "maturityDate":
            if descending:
                rows = rows.order_by(cert_type.maturity_date.desc())
            else:
                rows = rows.order_by(cert_type.maturity_date.asc())
        if sort_key == "name":
            if descending:
                rows = rows.order_by(cert_type.name.desc())
            else:
                rows = rows.order_by(cert_type.name.asc())
        results = [post.to_dict() for post in rows.all()]
    count = len(results)
    return paginate(results), HTTPStatus.OK, {"X-Total-Count": count}
