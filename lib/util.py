import hashlib
import pprint
from datetime import date, datetime, timedelta
from http import HTTPStatus
from typing import List, Optional

from croniter import croniter
from flask import Response, jsonify


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


def error_response(
    message: str, status_code: HTTPStatus
) -> tuple[Response, HTTPStatus]:
    return (
        jsonify({"message": message}),
        status_code,
    )


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
    but Instrument.identifier is `f"{location}_{symbol}"`. Matching must follow
    that per-type identifier, not the raw row id.

    For an Instrument target, the currency it holds is represented by its
    `symbol` (e.g. a high-yield savings sweep with symbol "USD"), not by its
    `currency` column -- that column is the currency used to buy/sell the
    instrument itself (e.g. the dividend/purchase currency of an AAPL position).
    """
    from models.instrument import Instrument
    from models.models import Account

    if not target_asset_id or not source_currency:
        return False
    source_currency = source_currency.upper()
    account = (
        session.query(Account).filter_by(user_id=user_id, id=target_asset_id).first()
    )
    if account:
        return account.currency.upper() == source_currency
    return any(
        f"{row.location}_{row.symbol}" == target_asset_id
        and row.symbol.upper() == source_currency
        for row in session.query(Instrument).filter_by(user_id=user_id).all()
    )


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
