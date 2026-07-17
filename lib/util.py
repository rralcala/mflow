import hashlib
import pprint
from datetime import date, datetime, timedelta
from typing import List, Optional

from croniter import croniter


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
