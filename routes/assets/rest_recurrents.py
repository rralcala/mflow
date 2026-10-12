import math
import re
from http import HTTPStatus

from flask import jsonify, request
from flask_login import current_user

from data.asset_store import reload_asset_store
from lib.config import Config
from lib.logger import get_logger
from lib.parsers import ParseError, available_parsers, get_parser, transaction_hashes
from lib.parsers.base import DATE, MAX_UPLOAD_BYTES, YEAR_MONTH
from lib.user_config import UserStore
from lib.util import (
    country_for_update,
    error_response,
    normalize_country,
    normalize_currency,
    paginate,
    recurrence_error,
    require_date,
    target_country_error,
    validate_date,
    validate_target_asset,
)
from models.models import IgnoredTransaction, Recurrent, RecurrentTransaction

from ..blueprints import assets_bp
from ..security import auth

Logger = get_logger()

IMPORT_HASH = re.compile(r"^[0-9a-f]{64}$")


def owns_recurrent(session, identifier) -> bool:
    return (
        session.query(Recurrent)
        .filter_by(user_id=int(current_user.id), identifier=identifier)
        .first()
        is not None
    )


@assets_bp.route("/recurrentTransactions", methods=["GET", "POST"])
@assets_bp.auth_required(auth)
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
            if not owns_recurrent(session, new_transaction.parent_id):
                return error_response("Unknown recurrent", HTTPStatus.BAD_REQUEST)
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
            if "description" in request.args:
                base_query = base_query.filter(
                    RecurrentTransaction.description.contains(
                        request.args["description"]
                    ),
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

        count = len(results)
        response = jsonify(paginate(results))
        response.headers["X-Total-Count"] = count
    return response, HTTPStatus.OK


@assets_bp.route("/recurrentTransactions/<name>", methods=["GET", "PUT", "DELETE"])
@assets_bp.auth_required(auth)
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
            parent_id = data.get("recurrentId", result.parent_id)
            if parent_id != result.parent_id and not owns_recurrent(session, parent_id):
                return error_response("Unknown recurrent", HTTPStatus.BAD_REQUEST)
            result.year_month = data.get("yearMonth", result.year_month)
            result.paid_with = data.get("paidWithAssetId", result.paid_with)
            result.transaction_date = data.get(
                "transactionDate", result.transaction_date
            )
            result.parent_id = parent_id
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
@assets_bp.auth_required(auth)
def recurrents_all():
    if request.method == "POST":
        data = request.json
        country = normalize_country(data.get("country"))
        target_asset_id = data.get("targetAssetId")
        currency = normalize_currency(data.get("currency"))
        start = require_date(data.get("start"), "start")
        end = require_date(data.get("end"), "end")
        error = recurrence_error(data.get("recurrence"))
        if error:
            return error_response(error, HTTPStatus.BAD_REQUEST)
        with Config.DB_SESSION() as session:
            if not validate_target_asset(
                session, int(current_user.id), target_asset_id, currency
            ):
                return jsonify({"message": "Bad target asset"}), HTTPStatus.BAD_REQUEST
            error = target_country_error(
                session, int(current_user.id), target_asset_id, country
            )
            if error:
                return error_response(error, HTTPStatus.BAD_REQUEST)
            new_transaction = Recurrent(
                identifier=data.get("id"),
                parent_asset_id=data.get("assetId"),
                target_asset_id=target_asset_id,
                country=country,
                amount=data.get("amount"),
                currency=currency,
                recurrence=data.get("recurrence"),
                start=start,
                end=end,
                flow_class=data.get("flowClass").lower(),
                rate=data.get("rate"),
                user_id=int(current_user.id),
                inflation=1 if data.get("inflation") else 0,
            )
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
            if "targetAssetId" in request.args:
                base_query = base_query.filter_by(
                    target_asset_id=request.args["targetAssetId"]
                )

            rows = base_query.all()

        results = sorted(
            [post.to_dict() for post in rows], key=lambda x: x.get("id", "")
        )
        count = len(results)
        response = jsonify(paginate(results))
        response.headers["X-Total-Count"] = count
        return response, HTTPStatus.OK


@assets_bp.route("/recurrents/<name>", methods=["GET", "PUT", "DELETE"])
@assets_bp.auth_required(auth)
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
            recurrence = data.get("recurrence", result.recurrence)
            if recurrence != result.recurrence:
                error = recurrence_error(recurrence)
                if error:
                    return error_response(error, HTTPStatus.BAD_REQUEST)
            target_asset_id = data.get("targetAssetId", result.target_asset_id)
            currency = normalize_currency(data.get("currency", result.currency))
            start = require_date(data.get("start", result.start), "start")
            end = require_date(data.get("end", result.end), "end")
            country = country_for_update(data, result.country)
            if not validate_target_asset(
                session, int(current_user.id), target_asset_id, currency
            ):
                return jsonify({"message": "Bad target asset"}), HTTPStatus.BAD_REQUEST
            error = target_country_error(
                session, int(current_user.id), target_asset_id, country
            )
            if error:
                return error_response(error, HTTPStatus.BAD_REQUEST)
            result.parent_asset_id = data.get("assetId", result.parent_asset_id)
            result.target_asset_id = target_asset_id
            result.country = country
            result.amount = data.get("amount", result.amount)
            result.currency = currency
            result.recurrence = recurrence
            result.start = start
            result.end = end
            result.flow_class = data.get("flowClass", result.flow_class).lower()
            result.rate = data.get("rate", result.rate)
            result.inflation = 1 if data.get("inflation", result.inflation) else 0
            session.commit()
            reload_asset_store(UserStore.get_user_config(current_user.id))
        elif request.method == "DELETE":
            session.delete(result)
            session.commit()
            reload_asset_store(UserStore.get_user_config(current_user.id))
        return jsonify(result.to_dict()), HTTPStatus.OK


@assets_bp.route("/transactionParsers", methods=["GET"])
@assets_bp.auth_required(auth)
def transaction_parsers():
    results = sorted(
        (parser.to_dict() for parser in available_parsers().values()),
        key=lambda x: x["name"],
    )
    count = len(results)
    response = jsonify(paginate(results))
    response.headers["X-Total-Count"] = count
    return response, HTTPStatus.OK


def processed_rows(session, hashes):
    """The caller's imported and ignored rows among `hashes`, keyed by hash."""
    if not hashes:
        return {}, {}
    user_id = int(current_user.id)
    imported = (
        session.query(RecurrentTransaction)
        .filter(
            RecurrentTransaction.user_id == user_id,
            RecurrentTransaction.import_hash.in_(hashes),
        )
        .all()
    )
    ignored = (
        session.query(IgnoredTransaction)
        .filter(
            IgnoredTransaction.user_id == user_id,
            IgnoredTransaction.import_hash.in_(hashes),
        )
        .all()
    )
    return (
        {row.import_hash: row for row in imported},
        {row.import_hash: row for row in ignored},
    )


@assets_bp.route("/recurrentTransactionsParse", methods=["POST"])
@assets_bp.auth_required(auth)
def recurrent_transactions_parse():
    """Parse an uploaded statement into transactions, without saving them.

    Multipart form with `file` and `parser` (a `/transactionParsers` id). The
    file must have one of the parser's extensions and be at most
    MAX_UPLOAD_BYTES. Each returned row carries its import hash and a `status`:
    `new`, `ignored`, or `imported`, in which case the row holds the saved
    transaction's values and `transactionId`.
    """
    parser = get_parser(request.form.get("parser", ""))
    if parser is None:
        return error_response("Unknown parser", HTTPStatus.BAD_REQUEST)
    upload = request.files.get("file")
    if upload is None:
        return error_response("Missing file", HTTPStatus.BAD_REQUEST)
    filename = upload.filename or ""
    if not parser.accepts(filename):
        return error_response(
            f"{parser.name} only reads {', '.join(parser.extensions)} files",
            HTTPStatus.BAD_REQUEST,
        )
    content = upload.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        return error_response(
            "File is larger than 1.5 MB", HTTPStatus.REQUEST_ENTITY_TOO_LARGE
        )
    try:
        transactions = parser.parse(content, filename)
    except ParseError as e:
        return error_response(str(e), HTTPStatus.BAD_REQUEST)

    hashes = transaction_hashes(transactions)
    with Config.DB_SESSION() as session:
        imported, ignored = processed_rows(session, hashes)
    results = []
    for transaction, import_hash in zip(transactions, hashes):
        row = {
            "importHash": import_hash,
            "transactionDate": transaction.transaction_date,
            "yearMonth": transaction.year_month or transaction.transaction_date[:7],
            "description": transaction.description,
            "amount": transaction.amount,
            "recurrentId": transaction.recurrent_id,
            "paidWithAssetId": transaction.paid_with,
            "status": "new",
            "transactionId": None,
        }
        if import_hash in imported:
            # Show what was saved, which may differ from the file after edits.
            saved = imported[import_hash].to_dict()
            row.update(
                {
                    key: saved[key]
                    for key in (
                        "yearMonth",
                        "description",
                        "amount",
                        "recurrentId",
                        "paidWithAssetId",
                    )
                },
                status="imported",
                transactionId=saved["id"],
            )
        elif import_hash in ignored:
            row["status"] = "ignored"
        results.append(row)
    return jsonify(results), HTTPStatus.OK


def source_row_error(row) -> str | None:
    """Checks shared by rows to import and rows to ignore."""
    if not isinstance(row, dict):
        return "not an object"
    if not IMPORT_HASH.match(str(row.get("importHash", ""))):
        return "invalid importHash"
    transaction_date = row.get("transactionDate")
    if (
        not isinstance(transaction_date, str)
        or not DATE.match(transaction_date)
        or not validate_date(transaction_date)
    ):
        return f"invalid transactionDate '{transaction_date}'"
    try:
        amount = float(row.get("amount"))
    except (TypeError, ValueError):
        amount = math.nan
    if not math.isfinite(amount):
        return f"invalid amount '{row.get('amount')}'"
    if len(str(row.get("description") or "")) > 200:
        return "description longer than 200 characters"
    return None


def import_row_error(row, owned_recurrents) -> str | None:
    error = source_row_error(row)
    if error:
        return error
    if row.get("recurrentId") not in owned_recurrents:
        return f"unknown recurrent '{row.get('recurrentId')}'"
    if not YEAR_MONTH.match(str(row.get("yearMonth") or row["transactionDate"][:7])):
        return f"invalid yearMonth '{row.get('yearMonth')}'"
    if not row.get("paidWithAssetId"):
        return "missing paidWithAssetId"
    return None


@assets_bp.route("/recurrentTransactionsImport", methods=["POST"])
@assets_bp.auth_required(auth)
def recurrent_transactions_import():
    """Save parsed rows as transactions, or record them as ignored.

    Body: `{"transactions": [...], "ignored": [...]}`, rows as returned by
    `/recurrentTransactionsParse`. Rows to import are shaped like a
    recurrentTransactions POST plus `importHash`; rows to ignore need
    `importHash`, `transactionDate`, `description` and `amount`. The whole batch
    is rejected if any row is invalid.

    Hashes already imported are skipped. Importing an ignored hash un-ignores
    it; ignoring an imported hash, or one also imported in this batch, is a
    no-op.
    """
    body = request.json or {}
    rows = body.get("transactions") or []
    ignore_rows = body.get("ignored") or []
    if not isinstance(rows, list) or not isinstance(ignore_rows, list):
        return error_response(
            "transactions and ignored must be lists", HTTPStatus.BAD_REQUEST
        )
    if not rows and not ignore_rows:
        return error_response("No transactions", HTTPStatus.BAD_REQUEST)
    user_id = int(current_user.id)
    with Config.DB_SESSION() as session:
        owned_recurrents = {
            row[0]
            for row in session.query(Recurrent.identifier)
            .filter_by(user_id=user_id)
            .all()
        }
        for index, row in enumerate(rows, start=1):
            error = import_row_error(row, owned_recurrents)
            if error:
                return error_response(
                    f"Transaction {index}: {error}", HTTPStatus.BAD_REQUEST
                )
        for index, row in enumerate(ignore_rows, start=1):
            error = source_row_error(row)
            if error:
                return error_response(
                    f"Ignored row {index}: {error}", HTTPStatus.BAD_REQUEST
                )

        imported, ignored = processed_rows(
            session, [row["importHash"] for row in rows + ignore_rows]
        )
        done = set(imported)
        inserted = 0
        for row in rows:
            import_hash = row["importHash"]
            if import_hash in done:
                continue
            done.add(import_hash)
            if import_hash in ignored:
                session.delete(ignored.pop(import_hash))
            session.add(
                RecurrentTransaction(
                    parent_id=row["recurrentId"],
                    year_month=row.get("yearMonth") or row["transactionDate"][:7],
                    description=str(row.get("description") or ""),
                    amount=str(float(row["amount"])),
                    transaction_date=row["transactionDate"],
                    paid_with=row["paidWithAssetId"],
                    user_id=user_id,
                    import_hash=import_hash,
                )
            )
            inserted += 1
        newly_ignored = 0
        for row in ignore_rows:
            import_hash = row["importHash"]
            if import_hash in done or import_hash in ignored:
                continue
            done.add(import_hash)
            session.add(
                IgnoredTransaction(
                    user_id=user_id,
                    import_hash=import_hash,
                    transaction_date=row["transactionDate"],
                    description=str(row.get("description") or ""),
                    amount=str(float(row["amount"])),
                )
            )
            newly_ignored += 1
        session.commit()
    if inserted:
        reload_asset_store(UserStore.get_user_config(current_user.id))
    return (
        jsonify(
            {
                "inserted": inserted,
                "ignored": newly_ignored,
                "skipped": len(rows) + len(ignore_rows) - inserted - newly_ignored,
            }
        ),
        HTTPStatus.CREATED,
    )
