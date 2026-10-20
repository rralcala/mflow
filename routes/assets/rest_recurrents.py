import math
import re
from http import HTTPStatus

from apiflask import abort
from flask_login import current_user

from data.asset_store import reload_asset_store
from lib.config import Config
from lib.logger import get_logger
from lib.parsers import ParseError, available_parsers, get_parser, transaction_hashes
from lib.parsers.base import DATE, MAX_UPLOAD_BYTES, YEAR_MONTH
from lib.user_config import UserStore
from lib.util import (
    country_for_update,
    normalize_country,
    normalize_currency,
    normalize_flow_class,
    owned_or_404,
    paginate,
    recurrence_error,
    require_date,
    require_number,
    target_country_error,
    validate_date,
    validate_target_asset,
)
from models.models import (
    Account,
    IgnoredTransaction,
    Recurrent,
    RecurrentTransaction,
)

from ..blueprints import assets_bp
from ..schemas import (
    ImportIn,
    ImportOut,
    PageQuery,
    ParsedRowOut,
    ParseIn,
    RecurrentIn,
    RecurrentOut,
    RecurrentsQuery,
    RecurrentTransactionIn,
    RecurrentTransactionOut,
    RecurrentTransactionsQuery,
    TotalCountHeader,
    TransactionParserOut,
)
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


def apply_to_balance(session, recurrent, transaction) -> str | None:
    """Add a transaction's amount to the balance of the account that paid it.

    Amounts are negative for spending and positive for income, so they are
    added as-is. Only Accounts in the recurrent's currency can be updated. The
    caller has already validated the transaction's amount.
    """
    account = (
        session.query(Account)
        .filter_by(user_id=int(current_user.id), id=transaction.paid_with)
        .first()
    )
    if account is None:
        return f"'{transaction.paid_with}' is not an account"
    if account.currency.upper() != recurrent.currency.upper():
        return (
            f"Account '{account.id}' holds {account.currency}, "
            f"not {recurrent.currency}"
        )
    account.balance = str(float(account.balance) + float(transaction.amount))
    return None


@assets_bp.get("/recurrentTransactions")
@assets_bp.auth_required(auth)
@assets_bp.input(RecurrentTransactionsQuery, location="query")
@assets_bp.output(RecurrentTransactionOut(many=True), headers=TotalCountHeader)
def recurrent_transactions_list(query_data):
    with Config.DB_SESSION() as session:
        base_query = session.query(Recurrent).filter_by(user_id=int(current_user.id))
        parent_recurrents = base_query.all()
        recurrents = {}
        for post in parent_recurrents:
            recurrents[post.identifier] = post.to_dict()

        base_query = session.query(RecurrentTransaction).filter(
            RecurrentTransaction.user_id == int(current_user.id)
        )
        if "recurrentId" in query_data:
            base_query = base_query.filter(
                RecurrentTransaction.parent_id == query_data["recurrentId"],
            )
        if "yearMonth" in query_data:
            base_query = base_query.filter(
                RecurrentTransaction.year_month == query_data["yearMonth"],
            )
        if "paidWithAssetId" in query_data:
            base_query = base_query.filter(
                RecurrentTransaction.paid_with == query_data["paidWithAssetId"],
            )
        if "description" in query_data:
            base_query = base_query.filter(
                RecurrentTransaction.description.contains(query_data["description"]),
            )
        results = []
        for post in base_query.order_by(
            RecurrentTransaction.transaction_date.desc()
        ).all():
            record = post.to_dict()
            record["currency"] = recurrents.get(post.parent_id, {}).get("currency", "")
            results.append(record)

    count = len(results)
    return paginate(results), HTTPStatus.OK, {"X-Total-Count": count}


@assets_bp.post("/recurrentTransactions")
@assets_bp.auth_required(auth)
@assets_bp.input(RecurrentTransactionIn)
@assets_bp.output(RecurrentTransactionOut, status_code=HTTPStatus.CREATED)
def recurrent_transaction_create(json_data):
    data = json_data
    new_transaction = RecurrentTransaction(
        parent_id=data.get("recurrentId"),
        year_month=data.get("yearMonth"),
        description=data.get("description"),
        amount=require_number(data.get("amount"), "amount"),
        transaction_date=data.get("transactionDate"),
        paid_with=data.get("paidWithAssetId"),
        user_id=int(current_user.id),
    )
    with Config.DB_SESSION() as session:
        recurrent = (
            session.query(Recurrent)
            .filter_by(
                user_id=int(current_user.id), identifier=new_transaction.parent_id
            )
            .first()
        )
        if recurrent is None:
            abort(HTTPStatus.BAD_REQUEST, "Unknown recurrent")
        if data.get("updateBalance"):
            error = apply_to_balance(session, recurrent, new_transaction)
            if error:
                abort(HTTPStatus.BAD_REQUEST, error)
        session.add(new_transaction)
        session.commit()
        reload_asset_store(UserStore.get_user_config(current_user.id))
        return new_transaction.to_dict()


@assets_bp.get("/recurrentTransactions/<name>")
@assets_bp.auth_required(auth)
@assets_bp.output(RecurrentTransactionOut)
def recurrent_transaction_get(name):
    with Config.DB_SESSION() as session:
        return find_transaction(session, name).to_dict()


@assets_bp.put("/recurrentTransactions/<name>")
@assets_bp.auth_required(auth)
@assets_bp.input(RecurrentTransactionIn(partial=True, exclude=("updateBalance",)))
@assets_bp.output(RecurrentTransactionOut)
def recurrent_transaction_update(name, json_data):
    data = json_data
    with Config.DB_SESSION() as session:
        result = find_transaction(session, name)
        parent_id = data.get("recurrentId", result.parent_id)
        if parent_id != result.parent_id and not owns_recurrent(session, parent_id):
            abort(HTTPStatus.BAD_REQUEST, "Unknown recurrent")
        result.year_month = data.get("yearMonth", result.year_month)
        result.paid_with = data.get("paidWithAssetId", result.paid_with)
        result.transaction_date = data.get("transactionDate", result.transaction_date)
        result.parent_id = parent_id
        result.amount = require_number(data.get("amount", result.amount), "amount")
        result.description = data.get("description", result.description)
        session.commit()
        reload_asset_store(UserStore.get_user_config(current_user.id))
        return result.to_dict()


@assets_bp.delete("/recurrentTransactions/<name>")
@assets_bp.auth_required(auth)
@assets_bp.output(RecurrentTransactionOut)
def recurrent_transaction_delete(name):
    with Config.DB_SESSION() as session:
        result = find_transaction(session, name)
        session.delete(result)
        session.commit()
        reload_asset_store(UserStore.get_user_config(current_user.id))
        return result.to_dict()


def find_transaction(session, name) -> RecurrentTransaction:
    return owned_or_404(
        session,
        RecurrentTransaction,
        int(current_user.id),
        "Recurrent Transaction not found",
        transaction_id=name,
    )


@assets_bp.get("/recurrents")
@assets_bp.auth_required(auth)
@assets_bp.input(RecurrentsQuery, location="query")
@assets_bp.output(RecurrentOut(many=True), headers=TotalCountHeader)
def recurrents_list(query_data):
    with Config.DB_SESSION() as session:
        base_query = session.query(Recurrent).filter_by(user_id=int(current_user.id))
        if "flowClass" in query_data:
            base_query = base_query.filter_by(flow_class=query_data["flowClass"])
        if "targetAssetId" in query_data:
            base_query = base_query.filter_by(
                target_asset_id=query_data["targetAssetId"]
            )

        rows = base_query.all()

    results = sorted([post.to_dict() for post in rows], key=lambda x: x.get("id", ""))
    count = len(results)
    return paginate(results), HTTPStatus.OK, {"X-Total-Count": count}


@assets_bp.post("/recurrents")
@assets_bp.auth_required(auth)
@assets_bp.input(RecurrentIn)
@assets_bp.output(RecurrentOut, status_code=HTTPStatus.CREATED)
def recurrent_create(json_data):
    data = json_data
    country = normalize_country(data.get("country"))
    target_asset_id = data.get("targetAssetId")
    currency = normalize_currency(data.get("currency"))
    start = require_date(data.get("start"), "start")
    end = require_date(data.get("end"), "end")
    amount = require_number(data.get("amount"), "amount")
    rate = require_number(data.get("rate"), "rate")
    flow_class = normalize_flow_class(data.get("flowClass"))
    error = recurrence_error(data.get("recurrence"))
    if error:
        abort(HTTPStatus.BAD_REQUEST, error)
    with Config.DB_SESSION() as session:
        if not validate_target_asset(
            session, int(current_user.id), target_asset_id, currency
        ):
            abort(HTTPStatus.BAD_REQUEST, "Bad target asset")
        error = target_country_error(
            session, int(current_user.id), target_asset_id, country
        )
        if error:
            abort(HTTPStatus.BAD_REQUEST, error)
        new_transaction = Recurrent(
            identifier=data.get("id"),
            parent_asset_id=data.get("assetId"),
            target_asset_id=target_asset_id,
            country=country,
            amount=amount,
            currency=currency,
            recurrence=data.get("recurrence"),
            start=start,
            end=end,
            flow_class=flow_class,
            rate=rate,
            user_id=int(current_user.id),
            inflation=1 if data.get("inflation") else 0,
        )
        session.add(new_transaction)
        session.commit()
        reload_asset_store(UserStore.get_user_config(current_user.id))
        return new_transaction.to_dict()


@assets_bp.get("/recurrents/<name>")
@assets_bp.auth_required(auth)
@assets_bp.output(RecurrentOut)
def recurrent_get(name):
    with Config.DB_SESSION() as session:
        return find_recurrent(session, name).to_dict()


@assets_bp.put("/recurrents/<name>")
@assets_bp.auth_required(auth)
@assets_bp.input(RecurrentIn(partial=True, exclude=("id",)))
@assets_bp.output(RecurrentOut)
def recurrent_update(name, json_data):
    data = json_data
    with Config.DB_SESSION() as session:
        result = find_recurrent(session, name)
        recurrence = data.get("recurrence", result.recurrence)
        if recurrence != result.recurrence:
            error = recurrence_error(recurrence)
            if error:
                abort(HTTPStatus.BAD_REQUEST, error)
        target_asset_id = data.get("targetAssetId", result.target_asset_id)
        currency = normalize_currency(data.get("currency", result.currency))
        start = require_date(data.get("start", result.start), "start")
        end = require_date(data.get("end", result.end), "end")
        amount = require_number(data.get("amount", result.amount), "amount")
        rate = require_number(data.get("rate", result.rate), "rate")
        flow_class = normalize_flow_class(data.get("flowClass", result.flow_class))
        country = country_for_update(data, result.country)
        if not validate_target_asset(
            session, int(current_user.id), target_asset_id, currency
        ):
            abort(HTTPStatus.BAD_REQUEST, "Bad target asset")
        error = target_country_error(
            session, int(current_user.id), target_asset_id, country
        )
        if error:
            abort(HTTPStatus.BAD_REQUEST, error)
        result.parent_asset_id = data.get("assetId", result.parent_asset_id)
        result.target_asset_id = target_asset_id
        result.country = country
        result.amount = amount
        result.currency = currency
        result.recurrence = recurrence
        result.start = start
        result.end = end
        result.flow_class = flow_class
        result.rate = rate
        result.inflation = 1 if data.get("inflation", result.inflation) else 0
        session.commit()
        reload_asset_store(UserStore.get_user_config(current_user.id))
        return result.to_dict()


@assets_bp.delete("/recurrents/<name>")
@assets_bp.auth_required(auth)
@assets_bp.output(RecurrentOut)
def recurrent_delete(name):
    with Config.DB_SESSION() as session:
        result = find_recurrent(session, name)
        session.delete(result)
        session.commit()
        reload_asset_store(UserStore.get_user_config(current_user.id))
        return result.to_dict()


def find_recurrent(session, name) -> Recurrent:
    return owned_or_404(
        session, Recurrent, int(current_user.id), "Recurrent not found", identifier=name
    )


@assets_bp.get("/transactionParsers")
@assets_bp.auth_required(auth)
@assets_bp.input(PageQuery, location="query")
@assets_bp.output(TransactionParserOut(many=True), headers=TotalCountHeader)
def transaction_parsers(query_data):
    results = sorted(
        (parser.to_dict() for parser in available_parsers().values()),
        key=lambda x: x["name"],
    )
    count = len(results)
    return paginate(results), HTTPStatus.OK, {"X-Total-Count": count}


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


@assets_bp.post("/recurrentTransactionsParse")
@assets_bp.auth_required(auth)
@assets_bp.input(ParseIn, location="files")
@assets_bp.output(ParsedRowOut(many=True))
def recurrent_transactions_parse(files_data):
    """Parse an uploaded statement into transactions, without saving them.

    The file must have one of the parser's extensions and be at most
    MAX_UPLOAD_BYTES. Each returned row carries its import hash and a `status`:
    `new`, `ignored`, or `imported`, in which case the row holds the saved
    transaction's values and `transactionId`.
    """
    parser = get_parser(files_data["parser"])
    if parser is None:
        abort(HTTPStatus.BAD_REQUEST, "Unknown parser")
    upload = files_data["file"]
    filename = upload.filename or ""
    if not parser.accepts(filename):
        abort(
            HTTPStatus.BAD_REQUEST,
            f"{parser.name} only reads {', '.join(parser.extensions)} files",
        )
    content = upload.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        abort(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "File is larger than 1.5 MB")
    try:
        transactions = parser.parse(content, filename)
    except ParseError as e:
        abort(HTTPStatus.BAD_REQUEST, str(e))

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
    return results


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


# The schema documents the body; the rows are checked below instead, so an
# error names the row by its position ("Transaction 2: ...") and the whole
# batch is rejected.
@assets_bp.post("/recurrentTransactionsImport")
@assets_bp.auth_required(auth)
@assets_bp.input(ImportIn, validation=False)
@assets_bp.output(ImportOut, status_code=HTTPStatus.CREATED)
def recurrent_transactions_import(json_data):
    """Save parsed rows as transactions, or record them as ignored.

    Rows are as returned by `/recurrentTransactionsParse`. Rows to import are
    shaped like a recurrentTransactions POST plus `importHash`; rows to ignore
    need `importHash`, `transactionDate`, `description` and `amount`. The whole
    batch is rejected if any row is invalid.

    Hashes already imported are skipped. Importing an ignored hash un-ignores
    it; ignoring an imported hash, or one also imported in this batch, is a
    no-op.
    """
    body = json_data if isinstance(json_data, dict) else {}
    rows = body.get("transactions") or []
    ignore_rows = body.get("ignored") or []
    if not isinstance(rows, list) or not isinstance(ignore_rows, list):
        abort(HTTPStatus.BAD_REQUEST, "transactions and ignored must be lists")
    if not rows and not ignore_rows:
        abort(HTTPStatus.BAD_REQUEST, "No transactions")
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
                abort(HTTPStatus.BAD_REQUEST, f"Transaction {index}: {error}")
        for index, row in enumerate(ignore_rows, start=1):
            error = source_row_error(row)
            if error:
                abort(HTTPStatus.BAD_REQUEST, f"Ignored row {index}: {error}")

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
    return {
        "inserted": inserted,
        "ignored": newly_ignored,
        "skipped": len(rows) + len(ignore_rows) - inserted - newly_ignored,
    }
