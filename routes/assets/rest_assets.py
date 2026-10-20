from datetime import datetime
from http import HTTPStatus
from typing import Any, Dict, List, Optional

from apiflask import abort
from flask_login import current_user

from data.asset_store import get_asset_store, reload_asset_store
from data.exchange_rates import ExchangeRates
from lib.config import Config
from lib.logger import get_logger
from lib.user_config import UserStore
from lib.util import (
    country_for_update,
    normalize_country,
    normalize_currency,
    normalize_flow_class,
    owned_or_404,
    paginate,
    require_date,
    require_dividend,
    require_number,
    target_references,
    validate_date,
    validate_pool_target,
    validate_target_asset,
)
from models.instrument import Instrument
from models.models import Account
from models.payable import Payable
from models.property import Property
from reports.list_assets import asset_data_from_asset, get_assets
from reports.pnl import monthly_transactions as upcoming_monthly_transactions

from ..blueprints import assets_bp
from ..schemas import (
    AccountIn,
    AccountOut,
    AssetOut,
    AssetsQuery,
    DashboardBudgetOut,
    InstrumentIn,
    InstrumentOut,
    ListQuery,
    MessageOut,
    MonthlyTransactionOut,
    PageQuery,
    PayableIn,
    PayableOut,
    PayablesQuery,
    PropertyIn,
    PropertyOut,
    TotalCountHeader,
)
from ..security import auth

Logger = get_logger()


def account_transfer_error(
    session, transfer_by: Optional[str], target_asset_id: Optional[str], currency: str
) -> Optional[str]:
    """A transfer-by date needs a valid date and a target pool in the same currency."""
    if not transfer_by:
        return None
    if not validate_date(transfer_by):
        return f"Invalid date '{transfer_by}'"
    if not target_asset_id:
        return "A target pool is required when a transfer-by date is set"
    if not validate_pool_target(
        session, int(current_user.id), target_asset_id, currency
    ):
        return "The target must be a target pool in the account's currency"
    return None


@assets_bp.get("/accounts")
@assets_bp.auth_required(auth)
@assets_bp.input(ListQuery, location="query")
@assets_bp.output(AccountOut(many=True), headers=TotalCountHeader)
def accounts_list(query_data):
    with Config.DB_SESSION() as session:
        results = [
            post.to_dict()
            for post in session.query(Account)
            .filter_by(user_id=int(current_user.id))
            .all()
        ]
    count = len(results)
    if "sort" in query_data:
        sort_key = query_data["sort"]
        reverse = query_data.get("order", "ASC") == "DESC"
        results.sort(key=lambda x: x.get(sort_key, ""), reverse=reverse)
    return paginate(results), HTTPStatus.OK, {"X-Total-Count": count}


@assets_bp.post("/accounts")
@assets_bp.auth_required(auth)
@assets_bp.input(AccountIn)
@assets_bp.output(AccountOut, status_code=HTTPStatus.CREATED)
def account_create(json_data):
    data = json_data
    with Config.DB_SESSION() as session:
        new_transaction = Account(
            id=data.get("id"),
            country=normalize_country(data.get("country")),
            institution=data.get("institution"),
            currency=normalize_currency(data.get("currency")),
            balance=require_number(data.get("balance"), "balance"),
            factor=require_number(data.get("factor"), "factor"),
            account_type=data.get("accountType"),
            liquid=1 if data.get("liquid") else 0,
            user_id=int(current_user.id),
            transfer_by=data.get("transferBy") or None,
            target_asset_id=data.get("targetAssetId") or None,
        )
        error = account_transfer_error(
            session,
            new_transaction.transfer_by,
            new_transaction.target_asset_id,
            new_transaction.currency,
        )
        if error:
            abort(HTTPStatus.BAD_REQUEST, error)
        session.add(new_transaction)
        session.commit()
        reload_asset_store(UserStore.get_user_config(current_user.id))
        return new_transaction.to_dict()


@assets_bp.get("/assets/<identifier:id>")
@assets_bp.auth_required(auth)
@assets_bp.output(AssetOut)
def asset_get(id):
    Logger.info(f"Fetching asset with id: {id} for user: {current_user.id}")
    assets = get_asset_store(UserStore.get_user_config(current_user.id))

    for sub in assets.values():
        for asset in sub:
            if asset.get_identifier() == id:
                return asset_data_from_asset(asset)
    abort(HTTPStatus.NOT_FOUND, "Asset not found")


@assets_bp.get("/assets")
@assets_bp.auth_required(auth)
@assets_bp.input(AssetsQuery, location="query")
@assets_bp.output(AssetOut(many=True), headers=TotalCountHeader)
def assets(query_data):
    user_config = UserStore.get_user_config(current_user.id)
    results = get_assets(
        get_asset_store(user_config),
        liquid_only=query_data.get("liquid", False),
        target_pools_only=query_data.get("targetPool", False),
    )

    if "id" in query_data:
        ids = set(query_data["id"])
        results = [r for r in results if r.get("id") in ids]
    count = len(results)

    if "sort" in query_data:
        sort_key = query_data["sort"]
        reverse = query_data.get("order", "ASC") == "DESC"
        results.sort(key=lambda x: x.get(sort_key, ""), reverse=reverse)
    return paginate(results), HTTPStatus.OK, {"X-Total-Count": count}


@assets_bp.get("/accounts/<identifier:name>")
@assets_bp.auth_required(auth)
@assets_bp.output(AccountOut)
def account_get(name):
    with Config.DB_SESSION() as session:
        return find_account(session, name).to_dict()


@assets_bp.put("/accounts/<identifier:name>")
@assets_bp.auth_required(auth)
@assets_bp.input(AccountIn(partial=True, exclude=("id",)))
@assets_bp.output(AccountOut)
def account_update(name, json_data):
    data = json_data
    with Config.DB_SESSION() as session:
        result = find_account(session, name)
        result.country = country_for_update(data, result.country)
        result.institution = data.get("institution", result.institution)
        result.currency = normalize_currency(data.get("currency", result.currency))
        result.balance = require_number(data.get("balance", result.balance), "balance")
        result.factor = require_number(data.get("factor", result.factor), "factor")
        result.account_type = data.get("accountType", result.account_type)
        result.liquid = 1 if data.get("liquid", result.liquid) else 0
        result.transfer_by = data.get("transferBy", result.transfer_by) or None
        result.target_asset_id = (
            data.get("targetAssetId", result.target_asset_id) or None
        )
        error = account_transfer_error(
            session, result.transfer_by, result.target_asset_id, result.currency
        )
        if error:
            abort(HTTPStatus.BAD_REQUEST, error)
        session.commit()
        reload_asset_store(UserStore.get_user_config(current_user.id))
        return result.to_dict()


@assets_bp.delete("/accounts/<identifier:name>")
@assets_bp.auth_required(auth)
@assets_bp.output(AccountOut)
def account_delete(name):
    with Config.DB_SESSION() as session:
        result = find_account(session, name)
        session.delete(result)
        session.commit()
        reload_asset_store(UserStore.get_user_config(current_user.id))
        return result.to_dict()


def find_account(session, name) -> Account:
    return owned_or_404(
        session, Account, int(current_user.id), "Account not found", id=name
    )


def instrument_target_ok(session, row: Instrument, target_asset_id: str) -> bool:
    """A target pool may target itself (e.g. a sweep compounding its interest);
    it's checked against the submitted row because it may not be saved yet."""
    if target_asset_id == f"{row.location}_{row.symbol}":
        return bool(row.is_target_pool) and (
            str(row.symbol).upper() == str(row.currency).upper()
        )
    return validate_target_asset(
        session, int(current_user.id), target_asset_id, row.currency
    )


def instrument_sale_error(sell_by: Optional[str], is_target_pool: int) -> Optional[str]:
    """Any instrument can be sold except target pools, which hold others' cash."""
    if not sell_by:
        return None
    if not validate_date(sell_by):
        return f"Invalid date '{sell_by}'"
    if is_target_pool:
        return "Target pools can't have a sell-by date"
    return None


def instrument_symbol_error(symbol) -> Optional[str]:
    """Instruments are valued from quotes when assets load, so the symbol needs one."""
    if not isinstance(symbol, str) or not symbol:
        return "symbol is required"
    try:
        ExchangeRates.exchange_rate(symbol)
    except ValueError:
        return f"No quote for symbol '{symbol}'"
    return None


@assets_bp.get("/instruments")
@assets_bp.auth_required(auth)
@assets_bp.input(ListQuery, location="query")
@assets_bp.output(InstrumentOut(many=True), headers=TotalCountHeader)
def instruments_list(query_data):
    with Config.DB_SESSION() as session:
        results = [
            post.to_dict()
            for post in session.query(Instrument)
            .filter_by(user_id=int(current_user.id))
            .all()
        ]
    count = len(results)
    if "sort" in query_data:
        if query_data["sort"] == "id":
            sort_key = "location"
        else:
            sort_key = query_data["sort"]
        reverse = query_data.get("order", "ASC") == "DESC"
        results.sort(key=lambda x: x.get(sort_key, ""), reverse=reverse)
    return paginate(results), HTTPStatus.OK, {"X-Total-Count": count}


@assets_bp.post("/instruments")
@assets_bp.auth_required(auth)
@assets_bp.input(InstrumentIn)
@assets_bp.output(InstrumentOut, status_code=HTTPStatus.CREATED)
def instrument_create(json_data):
    data = json_data
    country = normalize_country(data.get("country"))
    acquisition_date = data.get("acquisition_date")
    if not validate_date(acquisition_date):
        abort(HTTPStatus.BAD_REQUEST, f"Invalid date '{acquisition_date}'")
    target_asset_id = data.get("targetAssetId")
    currency = normalize_currency(data.get("currency"))
    with Config.DB_SESSION() as session:
        new_transaction = Instrument(
            country=country,
            location=data.get("location"),
            symbol=data.get("symbol"),
            currency=currency,
            factor=require_number(data.get("factor"), "factor"),
            qty=require_number(data.get("qty"), "qty"),
            dividend=require_dividend(data.get("dividend")),
            dividend_rate=require_number(data.get("dividend_rate"), "dividend_rate"),
            user_id=int(current_user.id),
            acquisition_date=acquisition_date,
            acquisition_price=require_number(
                data.get("acquisition_price"), "acquisition_price"
            ),
            liquid=1 if data.get("liquid") else 0,
            capital_rate=require_number(data.get("capital_rate", 0.0), "capital_rate"),
            target_asset_id=target_asset_id,
            sell_by=data.get("sellBy") or None,
            is_target_pool=1 if data.get("isTargetPool") else 0,
        )
        if not instrument_target_ok(session, new_transaction, target_asset_id):
            abort(HTTPStatus.BAD_REQUEST, "Bad target asset")
        error = instrument_sale_error(
            new_transaction.sell_by, new_transaction.is_target_pool
        )
        if error:
            abort(HTTPStatus.BAD_REQUEST, error)
        error = instrument_symbol_error(new_transaction.symbol)
        if error:
            abort(HTTPStatus.BAD_REQUEST, error)
        session.add(new_transaction)
        session.commit()
        reload_asset_store(UserStore.get_user_config(current_user.id))
        return new_transaction.to_dict()


@assets_bp.get("/instruments/<int:id>")
@assets_bp.auth_required(auth)
@assets_bp.output(InstrumentOut)
def instrument_get(id):
    with Config.DB_SESSION() as session:
        return find_instrument(session, id).to_dict()


@assets_bp.put("/instruments/<int:id>")
@assets_bp.auth_required(auth)
@assets_bp.input(InstrumentIn(partial=True))
@assets_bp.output(InstrumentOut)
def instrument_update(id, json_data):
    data = json_data
    with Config.DB_SESSION() as session:
        result = find_instrument(session, id)
        acquisition_date = data.get("acquisition_date")
        if not validate_date(acquisition_date):
            abort(HTTPStatus.BAD_REQUEST, f"Invalid date '{acquisition_date}'")
        target_asset_id = data.get("targetAssetId", result.target_asset_id)
        currency = normalize_currency(data.get("currency", result.currency))
        identifier = f"{result.location}_{result.symbol}"
        symbol = data.get("symbol", result.symbol)
        if symbol != result.symbol:
            error = instrument_symbol_error(symbol)
            if error:
                abort(HTTPStatus.BAD_REQUEST, error)
        was_target_pool = result.is_target_pool == 1
        result.country = country_for_update(data, result.country)
        result.location = data.get("location", result.location)
        result.symbol = symbol
        result.factor = require_number(data.get("factor", result.factor), "factor")
        result.qty = require_number(data.get("qty", result.qty), "qty")
        result.dividend = require_dividend(data.get("dividend", result.dividend))
        result.dividend_rate = require_number(
            data.get("dividend_rate", result.dividend_rate), "dividend_rate"
        )
        result.currency = currency
        result.acquisition_date = acquisition_date
        result.acquisition_price = require_number(
            data.get("acquisition_price", result.acquisition_price),
            "acquisition_price",
        )
        result.liquid = 1 if data.get("liquid", result.liquid) else 0
        result.capital_rate = require_number(
            data.get("capital_rate", result.capital_rate), "capital_rate"
        )
        result.target_asset_id = target_asset_id
        result.sell_by = data.get("sellBy", result.sell_by) or None
        result.is_target_pool = (
            1 if data.get("isTargetPool", result.is_target_pool) else 0
        )
        if was_target_pool and not result.is_target_pool:
            references = target_references(session, int(current_user.id), identifier)
            if references:
                abort(
                    HTTPStatus.BAD_REQUEST,
                    f"{identifier} is still the target of "
                    f"{', '.join(references)}; retarget them first",
                )
        if not instrument_target_ok(session, result, target_asset_id):
            abort(HTTPStatus.BAD_REQUEST, "Bad target asset")
        error = instrument_sale_error(result.sell_by, result.is_target_pool)
        if error:
            abort(HTTPStatus.BAD_REQUEST, error)
        session.commit()
        reload_asset_store(UserStore.get_user_config(current_user.id))
        return result.to_dict()


@assets_bp.delete("/instruments/<int:id>")
@assets_bp.auth_required(auth)
@assets_bp.output(InstrumentOut)
def instrument_delete(id):
    with Config.DB_SESSION() as session:
        result = find_instrument(session, id)
        session.delete(result)
        session.commit()
        reload_asset_store(UserStore.get_user_config(current_user.id))
        return result.to_dict()


def find_instrument(session, id) -> Instrument:
    return owned_or_404(
        session, Instrument, int(current_user.id), "Instrument not found", id=id
    )


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


@assets_bp.get("/monthlyTransactions")
@assets_bp.auth_required(auth)
@assets_bp.input(PageQuery, location="query")
@assets_bp.output(MonthlyTransactionOut(many=True), headers=TotalCountHeader)
def monthly_transactions(query_data):
    """Projected spending (negative amounts) for this month and the next."""
    response_items = []
    transactions = load_tx()
    for transaction in transactions:
        if transaction.get("amount", 0.0) < 0.0:
            response_items.append(transaction)
    count = len(response_items)
    return paginate(response_items), HTTPStatus.OK, {"X-Total-Count": count}


@assets_bp.get("/monthlyTransactions/<name>")
@assets_bp.auth_required(auth)
@assets_bp.output(MonthlyTransactionOut)
def monthly_transactions_get(name):
    for transaction in load_tx():
        if transaction.get("id") == name:
            return transaction
    abort(HTTPStatus.NOT_FOUND, "Transaction not found")


@assets_bp.get("/dashboardBudgets")
@assets_bp.auth_required(auth)
@assets_bp.input(PageQuery, location="query")
@assets_bp.output(DashboardBudgetOut(many=True), headers=TotalCountHeader)
def dashboard_budgets(query_data):
    """Remaining budget this month for the user's DASHBOARD_RECURRENTS."""
    user_config = UserStore.get_user_config(current_user.id)
    assets = {
        asset.get_identifier(): asset
        for currency_assets in get_asset_store(user_config).values()
        for asset in currency_assets
    }
    month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    response_items = []
    for entry in user_config.DASHBOARD_RECURRENTS:
        asset = assets.get(entry["id"])
        if asset is None:
            Logger.warning("Dashboard recurrent %s not found", entry["id"])
            continue
        amount, currency = asset.get_income_balance(month)
        budget, _ = asset.get_budgeted_income(month)
        response_items.append(
            {
                "id": entry["id"],
                "label": entry.get("label", entry["id"]),
                "amount": amount,
                "budget": budget,
                "currency": currency,
                "yearMonth": month.strftime("%Y-%m"),
            }
        )
    count = len(response_items)
    return paginate(response_items), HTTPStatus.OK, {"X-Total-Count": count}


@assets_bp.get("/payables")
@assets_bp.auth_required(auth)
@assets_bp.input(PayablesQuery, location="query")
@assets_bp.output(PayableOut(many=True), headers=TotalCountHeader)
def payables_list(query_data):
    with Config.DB_SESSION() as session:
        base_query = session.query(Payable).filter_by(user_id=int(current_user.id))
        if "flowClass" in query_data:
            base_query = base_query.filter_by(flow_class=query_data["flowClass"])

        results = [post.to_dict() for post in base_query.all()]
    count = len(results)
    if query_data.get("sort", "id") != "id":
        sort_key = query_data["sort"]
    else:
        sort_key = "dueDate"
    reverse = query_data.get("order", "ASC") == "DESC"
    results.sort(key=lambda x: x.get(sort_key, ""), reverse=reverse)
    return paginate(results), HTTPStatus.OK, {"X-Total-Count": count}


@assets_bp.post("/payables")
@assets_bp.auth_required(auth)
@assets_bp.input(PayableIn)
@assets_bp.output(PayableOut, status_code=HTTPStatus.CREATED)
def payable_create(json_data):
    data = json_data
    currency = normalize_currency(data.get("currency"))
    country = normalize_country(data.get("country"))
    due_date = require_date(data.get("dueDate"), "dueDate")
    amount = require_number(data.get("amount"), "amount")
    balance = require_number(data.get("balance"), "balance")
    flow_class = normalize_flow_class(data.get("flowClass"))
    target_asset_id = data.get("targetAssetId", data.get("paidWithAssetId"))
    with Config.DB_SESSION() as session:
        if not validate_target_asset(
            session, int(current_user.id), target_asset_id, currency
        ):
            abort(HTTPStatus.BAD_REQUEST, "Bad target asset")
        new_transaction = Payable(
            country=country,
            currency=currency,
            description=data.get("description"),
            amount=amount,
            balance=balance,
            due_date=due_date,
            commited=(1 if data.get("commited", False) else 0),
            user_id=int(current_user.id),
            flow_class=flow_class,
            target_asset_id=target_asset_id,
        )
        session.add(new_transaction)
        session.commit()
        reload_asset_store(UserStore.get_user_config(current_user.id))
        return new_transaction.to_dict()


@assets_bp.get("/payables/<int:id>")
@assets_bp.auth_required(auth)
@assets_bp.output(PayableOut)
def payable_get(id):
    with Config.DB_SESSION() as session:
        return find_payable(session, id).to_dict()


@assets_bp.put("/payables/<int:id>")
@assets_bp.auth_required(auth)
@assets_bp.input(PayableIn(partial=True))
@assets_bp.output(PayableOut)
def payable_update(id, json_data):
    data = json_data
    with Config.DB_SESSION() as session:
        result = find_payable(session, id)
        target_asset_id = data.get(
            "targetAssetId", data.get("paidWithAssetId", result.target_asset_id)
        )
        currency = normalize_currency(data.get("currency", result.currency))
        due_date = require_date(data.get("dueDate", result.due_date), "dueDate")
        amount = require_number(data.get("amount", result.amount), "amount")
        balance = require_number(data.get("balance", result.balance), "balance")
        flow_class = normalize_flow_class(data.get("flowClass", result.flow_class))
        if not validate_target_asset(
            session, int(current_user.id), target_asset_id, currency
        ):
            abort(HTTPStatus.BAD_REQUEST, "Bad target asset")
        result.country = country_for_update(data, result.country)
        result.currency = currency
        result.amount = amount
        result.balance = balance
        result.due_date = due_date
        result.description = data.get("description", result.description)
        result.commited = 1 if data.get("commited", result.commited) else 0
        result.flow_class = flow_class
        result.target_asset_id = target_asset_id
        session.commit()
        reload_asset_store(UserStore.get_user_config(current_user.id))
        return result.to_dict()


@assets_bp.delete("/payables/<int:id>")
@assets_bp.auth_required(auth)
@assets_bp.output(PayableOut)
def payable_delete(id):
    with Config.DB_SESSION() as session:
        result = find_payable(session, id)
        session.delete(result)
        session.commit()
        reload_asset_store(UserStore.get_user_config(current_user.id))
        return result.to_dict()


def find_payable(session, id) -> Payable:
    return owned_or_404(
        session, Payable, int(current_user.id), "Payable not found", id=id
    )


def property_sale_error(
    session, sell_by: Optional[str], target_asset_id: Optional[str], currency: str
) -> Optional[str]:
    """A sell-by date needs a valid date and a target asset to receive the sale."""
    if sell_by and not validate_date(sell_by):
        return f"Invalid date '{sell_by}'"
    if sell_by and not target_asset_id:
        return "A target asset is required when a sell-by date is set"
    if target_asset_id and not validate_target_asset(
        session, int(current_user.id), target_asset_id, currency
    ):
        return "Bad target asset"
    return None


@assets_bp.get("/properties")
@assets_bp.auth_required(auth)
@assets_bp.input(ListQuery, location="query")
@assets_bp.output(PropertyOut(many=True), headers=TotalCountHeader)
def properties_list(query_data):
    with Config.DB_SESSION() as session:
        base_query = session.query(Property).filter_by(user_id=int(current_user.id))

        results = [post.to_dict() for post in base_query.all()]
    count = len(results)
    sort_key = query_data.get("sort", "propertyName")
    reverse = query_data.get("order", "ASC") == "DESC"
    results.sort(key=lambda x: x.get(sort_key, ""), reverse=reverse)
    return paginate(results), HTTPStatus.OK, {"X-Total-Count": count}


@assets_bp.post("/properties")
@assets_bp.auth_required(auth)
@assets_bp.input(PropertyIn)
@assets_bp.output(PropertyOut, status_code=HTTPStatus.CREATED)
def property_create(json_data):
    data = json_data
    new_transaction = Property(
        user_id=int(current_user.id),
        country=normalize_country(data.get("country")),
        currency=normalize_currency(data.get("currency")),
        property_name=data.get("propertyName"),
        purchase_price=require_number(data.get("purchasePrice"), "purchasePrice"),
        purchase_date=require_date(data.get("purchaseDate"), "purchaseDate"),
        current_price=require_number(data.get("currentPrice"), "currentPrice"),
        rent_price=require_number(data.get("rentPrice"), "rentPrice"),
        depreciation=require_number(data.get("depreciation"), "depreciation"),
        additional_data=data.get("additionalData"),
        rent_currency=normalize_currency(data.get("rentCurrency")),
        sell_by=data.get("sellBy") or None,
        target_asset_id=data.get("targetAssetId") or None,
    )
    with Config.DB_SESSION() as session:
        error = property_sale_error(
            session,
            new_transaction.sell_by,
            new_transaction.target_asset_id,
            new_transaction.currency,
        )
        if error:
            abort(HTTPStatus.BAD_REQUEST, error)
        session.add(new_transaction)
        session.commit()
        reload_asset_store(UserStore.get_user_config(current_user.id))
        return new_transaction.to_dict()


@assets_bp.get("/properties/<int:id>")
@assets_bp.auth_required(auth)
@assets_bp.output(PropertyOut)
def property_get(id):
    with Config.DB_SESSION() as session:
        return find_property(session, id).to_dict()


@assets_bp.put("/properties/<int:id>")
@assets_bp.auth_required(auth)
@assets_bp.input(PropertyIn(partial=True))
@assets_bp.output(PropertyOut)
def property_update(id, json_data):
    data = json_data
    with Config.DB_SESSION() as session:
        result = find_property(session, id)
        result.country = country_for_update(data, result.country)
        result.currency = normalize_currency(data.get("currency", result.currency))
        result.property_name = data.get("propertyName", result.property_name)
        result.purchase_price = require_number(
            data.get("purchasePrice", result.purchase_price), "purchasePrice"
        )
        result.purchase_date = require_date(
            data.get("purchaseDate", result.purchase_date), "purchaseDate"
        )
        result.current_price = require_number(
            data.get("currentPrice", result.current_price), "currentPrice"
        )
        result.rent_price = require_number(
            data.get("rentPrice", result.rent_price), "rentPrice"
        )
        result.depreciation = require_number(
            data.get("depreciation", result.depreciation), "depreciation"
        )
        result.additional_data = data.get("additionalData", result.additional_data)
        result.rent_currency = normalize_currency(
            data.get("rentCurrency", result.rent_currency)
        )
        result.sell_by = data.get("sellBy", result.sell_by) or None
        result.target_asset_id = (
            data.get("targetAssetId", result.target_asset_id) or None
        )
        error = property_sale_error(
            session, result.sell_by, result.target_asset_id, result.currency
        )
        if error:
            abort(HTTPStatus.BAD_REQUEST, error)

        session.commit()
        reload_asset_store(UserStore.get_user_config(current_user.id))
        return result.to_dict()


@assets_bp.delete("/properties/<int:id>")
@assets_bp.auth_required(auth)
@assets_bp.output(PropertyOut)
def property_delete(id):
    with Config.DB_SESSION() as session:
        result = find_property(session, id)
        session.delete(result)
        session.commit()
        reload_asset_store(UserStore.get_user_config(current_user.id))
        return result.to_dict()


def find_property(session, id) -> Property:
    return owned_or_404(
        session, Property, int(current_user.id), "Property not found", id=id
    )


@assets_bp.get("/reload")
@assets_bp.auth_required(auth)
@assets_bp.output(MessageOut)
def reload_assets():
    reload_asset_store(UserStore.get_user_config(current_user.id))

    return {"message": "Assets reloaded"}
