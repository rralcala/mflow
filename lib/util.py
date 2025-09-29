import logging
from datetime import datetime, timedelta
from typing import List

from croniter import croniter


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


def config_logging(debug: bool):
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
