import hashlib
import math
import pprint
from datetime import date, datetime, timedelta
from http import HTTPStatus
from typing import List, Optional

from apiflask import abort
from croniter import CroniterError, croniter
from flask import request
from marshmallow import Schema

from data.constants import FLOW_CLASSES
from lib.config import Config


class FormatPrinter(pprint.PrettyPrinter):
    def __init__(self, formats, **kwargs):
        super(FormatPrinter, self).__init__(**kwargs)
        self.formats = formats

    def format(self, obj, ctx, maxlvl, lvl):
        if type(obj) in self.formats:
            # Use the specified format string
            return self.formats[type(obj)].format(obj), 1, 0
        return pprint.PrettyPrinter.format(self, obj, ctx, maxlvl, lvl)


PRINTER = FormatPrinter({float: "{:,.2f}", int: "{:d}"})


def validate_date(date_string: str, date_format="%Y-%m-%d") -> bool:
    if date_string is not None:
        try:
            datetime.strptime(date_string, date_format)
            return True
        except ValueError:
            pass
    return False


def paginate(items):
    """Slice a list by the request's json-server `_start` / `_end` arguments.

    Callers must take the X-Total-Count value *before* calling this, since the
    header reports the unsliced total. Non-list payloads are returned as is.
    """
    if not isinstance(items, list):
        return items
    if "_start" not in request.args and "_end" not in request.args:
        return items
    try:
        start = int(request.args.get("_start", 0))
        end = int(request.args["_end"]) if "_end" in request.args else None
    except ValueError:
        abort(400, "_start and _end must be integers")
    if start < 0 or (end is not None and end < 0):
        abort(400, "_start and _end must not be negative")
    return items[start:end]


def _sort_value(value):
    """Order numbers before strings before anything else, so mixed types never
    raise; strings compare case-insensitively."""
    if isinstance(value, (bool, int, float)):
        return (0, value, "")
    if isinstance(value, str):
        return (1, 0, value.casefold())
    return (2, 0, str(value))


def sort_items(items, query_data, schema, default=None, default_order="ASC"):
    """Sort records by the json-server `_sort` / `_order` arguments.

    Call it before `paginate()`, so slices come from the sorted list. `_sort`
    must be a field of the endpoint's output `schema` (400 otherwise); `_order`
    is ASC or DESC in any case. Without `_sort`, `default` / `default_order`
    apply, and with no default the items keep their order. Records whose value
    is missing or None go last in either direction.
    """
    key = query_data.get("sort") or default
    if not key:
        return items
    fields = schema.fields if isinstance(schema, Schema) else schema().fields
    allowed = sorted(field.data_key or name for name, field in fields.items())
    if key not in allowed:
        abort(400, f"Can't sort by '{key}'; expected one of {', '.join(allowed)}")
    order = query_data.get("order") or (
        "ASC" if query_data.get("sort") else default_order
    )
    order = order.upper()
    if order not in ("ASC", "DESC"):
        abort(400, "_order must be ASC or DESC")
    present = [item for item in items if item.get(key) is not None]
    missing = [item for item in items if item.get(key) is None]
    present.sort(key=lambda item: _sort_value(item[key]), reverse=order == "DESC")
    return present + missing


def normalize_country(value) -> str:
    """Return the upper-cased country code if it is one of Config.COUNTRIES.

    Anything else (missing, not a string, unknown code) is a 400 for the client,
    never a 500.
    """
    if value is None or value == "":
        abort(400, "country is required")
    if not isinstance(value, str):
        abort(400, "country must be a string")
    country = value.strip().upper()
    if country not in {c.upper() for c in Config.COUNTRIES}:
        abort(400, f"Invalid country '{value}'")
    return country


def country_for_update(data: dict, current: Optional[str]):
    """Country to store on a PUT: unchanged unless the payload changes it.

    A value equal to the stored one is accepted as is, so records holding a legacy
    country can still be edited; any new value is validated.
    """
    if "country" not in data or data["country"] == current:
        return current
    return normalize_country(data["country"])


def normalize_currency(value) -> str:
    """Return the upper-cased currency code if it is one of Config.CURRENCIES.

    The asset store groups assets by this code, so anything else is a 400.
    """
    if not isinstance(value, str) or not value.strip():
        abort(400, "currency is required")
    currency = value.strip().upper()
    if currency.lower() not in {c.lower() for c in Config.CURRENCIES}:
        abort(400, f"Invalid currency '{value}'")
    return currency


def require_date(value, field: str) -> str:
    """Dates are stored as YYYY-MM-DD strings and parsed when assets load."""
    if not isinstance(value, str) or not validate_date(value):
        abort(400, f"Invalid {field} '{value}', expected YYYY-MM-DD")
    return value


def require_number(value, field: str) -> str:
    """Numeric columns are strings that load_assets and to_dict() pass to float().

    Anything but a finite number (missing, null, a boolean, "abc", "nan") would
    save and then break every report, so it's a 400. Returns the stored form.
    """
    number = math.nan
    if isinstance(value, (int, float, str)) and not isinstance(value, bool):
        try:
            number = float(value)
        except ValueError:
            pass
    if not math.isfinite(number):
        abort(400, f"Invalid {field} '{value}', expected a number")
    return str(number)


NO_DIVIDEND = "N"


def require_dividend(value) -> str:
    """An instrument's dividend schedule: NO_DIVIDEND or a cron pattern.

    load_assets divides the dividend rate by the year's payouts, so the pattern
    must parse and actually fire; "0 0 30 2 *" passes croniter.is_valid but
    raises once runs are listed.
    """
    pattern = value.strip() if isinstance(value, str) else None
    if pattern and pattern.upper() == NO_DIVIDEND:
        return NO_DIVIDEND
    error = f"Invalid dividend '{value}', expected {NO_DIVIDEND} or a cron pattern"
    if not pattern or not croniter.is_valid(pattern):
        abort(400, error)
    try:
        croniter(pattern, datetime.now()).get_next(datetime)
    except CroniterError:  # never matches
        abort(400, error)
    return pattern


def normalize_flow_class(value) -> str:
    """Reports compare flow classes against RecurrentTypes in lower case."""
    flow_class = value.strip().lower() if isinstance(value, str) else None
    if flow_class not in FLOW_CLASSES:
        abort(
            400,
            f"Invalid flowClass '{value}', expected one of {', '.join(FLOW_CLASSES)}",
        )
    return flow_class


def owned_or_404(session, model, user_id: int, message: str, **filters):
    """The user's row of `model` matching `filters`, or a 404 with `message`."""
    row = session.query(model).filter_by(user_id=user_id, **filters).first()
    if row is None:
        abort(HTTPStatus.NOT_FOUND, message)
    return row


def validate_target_asset(
    session, user_id: int, target_asset_id: str, source_currency: str
) -> bool:
    """
    A target asset represents where cash is pulled from (cost-bearing flows) or
    deposited to (income flows). It must be an Account or an Instrument
    (e.g. an interest-bearing brokerage sweep) owned by the same user, and it
    must hold the same currency as the source asset being configured.

    Each asset type defines its own `identifier` (see asset_classes/*.py), which
    is not always the model's primary key: Account.identifier is its `id` column,
    but Instrument.identifier is `f"{location}_{account}_{symbol}"`. Matching must follow
    that per-type identifier, not the raw row id.

    For an Instrument target, the currency it holds is represented by its
    `symbol` (e.g. a high-yield savings sweep with symbol "USD"), not by its
    `currency` column -- that column is the currency used to buy/sell the
    instrument itself (e.g. the dividend/purchase currency of an AAPL position).
    Only instruments marked `is_target_pool` can be targets.
    """
    from models.models import Account

    if not target_asset_id or not source_currency:
        return False
    source_currency = source_currency.upper()
    account = (
        session.query(Account).filter_by(user_id=user_id, id=target_asset_id).first()
    )
    if account:
        return account.currency.upper() == source_currency
    return validate_pool_target(session, user_id, target_asset_id, source_currency)


def validate_pool_target(
    session, user_id: int, target_asset_id: str, source_currency: str
) -> bool:
    """Whether target_asset_id is a target-pool instrument holding the currency."""
    from models.instrument import Instrument

    if not target_asset_id or not source_currency:
        return False
    return any(
        row.identifier == target_asset_id
        and row.symbol.upper() == source_currency.upper()
        and row.is_target_pool == 1
        for row in session.query(Instrument).filter_by(user_id=user_id).all()
    )


def target_country(session, user_id: int, target_asset_id: str) -> Optional[str]:
    """Country of a target asset (an Account or an Instrument), if found."""
    from models.instrument import Instrument
    from models.models import Account

    account = (
        session.query(Account).filter_by(user_id=user_id, id=target_asset_id).first()
    )
    if account:
        return account.country
    for row in session.query(Instrument).filter_by(user_id=user_id).all():
        if row.identifier == target_asset_id:
            return row.country
    return None


def target_country_error(
    session, user_id: int, target_asset_id: str, country: str
) -> Optional[str]:
    """Flows must stay in their country: the target has to be in the same one."""
    found = target_country(session, user_id, target_asset_id)
    if (found or "").upper() != (country or "").upper():
        return (
            f"Target asset {target_asset_id} is in {found or 'no country'}, "
            f"but the recurrent is in {country}"
        )
    return None


def _identifier_labels():
    """Each asset model with how its per-type identifier is built from a row."""
    from models.bond import Bond
    from models.deposit_certificate import DepositCertificate
    from models.instrument import Instrument
    from models.models import Account, Recurrent
    from models.payable import Payable
    from models.property import Property

    return {
        Account: lambda row: row.id,
        Bond: lambda row: row.name,
        DepositCertificate: lambda row: row.name,
        Recurrent: lambda row: row.identifier,
        Payable: lambda row: row.description,
        Property: lambda row: row.property_name,
        Instrument: lambda row: row.identifier,
    }


def target_references(session, user_id: int, target_asset_id: str) -> List[str]:
    """Identifiers of the assets whose cash flows use target_asset_id."""
    references = []
    for model, label in _identifier_labels().items():
        for row in (
            session.query(model)
            .filter_by(user_id=user_id, target_asset_id=target_asset_id)
            .all()
        ):
            references.append(label(row))
    # A pool that compounds into itself doesn't count as a reference to it.
    return sorted(ref for ref in references if ref != target_asset_id)


def owns_asset(session, user_id: int, identifier: str) -> bool:
    """Whether the user has an asset of any type with this identifier."""
    return any(
        label(row) == identifier
        for model, label in _identifier_labels().items()
        for row in session.query(model).filter_by(user_id=user_id).all()
    )


def duplicate_error(
    session, user_id: int, identifier: str, exclude=None
) -> Optional[str]:
    """Why `identifier` can't be used: another of the user's assets, of any type,
    already has it. `exclude` is the row being updated, which may keep its own."""
    if not identifier:
        return None
    for model, label in _identifier_labels().items():
        for row in session.query(model).filter_by(user_id=user_id).all():
            if row is not exclude and label(row) == identifier:
                return f"An asset named '{identifier}' already exists"
    return None


def child_references(session, user_id: int, identifier: str) -> List[str]:
    """Assets that would be left dangling without `identifier`: those whose
    flows target it, and recurrents attached to it as their parent asset."""
    from models.models import Recurrent

    references = set(target_references(session, user_id, identifier))
    for row in (
        session.query(Recurrent)
        .filter_by(user_id=user_id, parent_asset_id=identifier)
        .all()
    ):
        if row.identifier != identifier:
            references.add(row.identifier)
    return sorted(references)


def children_error(
    session, user_id: int, identifier: str, action: str
) -> Optional[str]:
    """Why `identifier` can't be deleted or renamed, if other assets use it.
    `action` completes "Can't ..." (e.g. "delete", "rename")."""
    references = child_references(session, user_id, identifier)
    if not references:
        return None
    return (
        f"Can't {action} {identifier}: still used by {', '.join(references)}; "
        "retarget or remove them first"
    )


def reference_columns():
    """(model, column) pairs that hold another asset's identifier."""
    from models.bond import Bond
    from models.deposit_certificate import DepositCertificate
    from models.instrument import Instrument
    from models.models import Account, Recurrent, RecurrentTransaction
    from models.payable import Payable
    from models.property import Property

    return [
        (Account, "target_asset_id"),
        (Instrument, "target_asset_id"),
        (Recurrent, "target_asset_id"),
        (Recurrent, "parent_asset_id"),
        (Payable, "target_asset_id"),
        (Property, "target_asset_id"),
        (Bond, "target_asset_id"),
        (DepositCertificate, "target_asset_id"),
        (RecurrentTransaction, "paid_with"),
    ]


def rename_references(session, user_id: int, old: str, new: str) -> int:
    """Point every reference to `old` among the user's rows at `new`, so a
    rename doesn't leave other assets dangling. Rows already in the session
    (e.g. the one being renamed, if it targets itself) are updated in place.
    Returns how many references moved; the caller commits."""
    if not old or old == new:
        return 0
    moved = 0
    for model, column in reference_columns():
        for row in (
            session.query(model).filter_by(user_id=user_id, **{column: old}).all()
        ):
            setattr(row, column, new)
            moved += 1
    return moved


def type_to_str(type_obj) -> str:
    """
    Converts a type object to a string representation.
    """
    if hasattr(type_obj, "__name__"):
        return type_obj.__name__
    return str(type_obj)


def count_cron_runs(cron_pattern: str, start_date: datetime, end_date: datetime) -> int:
    return len(cron_runs(cron_pattern, start_date, end_date))


def cron_runs(
    cron_pattern: str, start_date: datetime, end_date: datetime
) -> List[datetime]:
    """
    Counts how many times a cron pattern runs between two dates.
    """
    dates = []
    if len(cron_pattern) > 1:
        start = start_date - timedelta(days=1)
        run_iter = croniter(cron_pattern, start)

        next_run = run_iter.get_next(datetime)
        while next_run <= end_date:
            dates.append(next_run)
            next_run = run_iter.get_next(datetime)
    return dates


def recurrence_error(cron_pattern) -> Optional[str]:
    """Recurrents may run at most once per calendar month.

    Transactions are recorded per year-month, so a pattern with several runs in
    a month can't be reconciled. Four years of runs cover leap-year patterns;
    the scan stops at the first month with two runs.
    """
    if not isinstance(cron_pattern, str) or not croniter.is_valid(cron_pattern):
        return f"Invalid recurrence '{cron_pattern}'"
    start = datetime(2024, 1, 1) - timedelta(seconds=1)
    end = datetime(2028, 1, 1)
    seen = set()
    try:
        run_iter = croniter(cron_pattern, start)
        next_run = run_iter.get_next(datetime)
        while next_run < end:
            month = (next_run.year, next_run.month)
            if month in seen:
                return f"Recurrence '{cron_pattern}' runs more than once a month"
            seen.add(month)
            next_run = run_iter.get_next(datetime)
    except CroniterError:  # e.g. a pattern that never matches, like Feb 30
        return f"Invalid recurrence '{cron_pattern}'"
    return None


def sha256_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def business_days_ago(days: int, from_date: Optional[date] = None) -> date:
    if days < 0:
        raise ValueError("days must be greater than or equal to 0")

    current_date = from_date
    if current_date is None:
        current_date = datetime.now().date()

    remaining_days = days
    while remaining_days > 0:
        current_date -= timedelta(days=1)
        if current_date.weekday() < 5:
            remaining_days -= 1

    return current_date
