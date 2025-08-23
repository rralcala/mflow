from datetime import datetime, timedelta

from croniter import croniter


def count_cron_runs(cron_pattern: str, start_date: datetime, end_date: datetime) -> int:
    """
    Counts how many times a cron pattern runs between two dates.
    """
    start = start_date - timedelta(days=1)
    if not cron_pattern:
        return 0
    run_iter = croniter(cron_pattern, start)
    count = 0
    next_run = run_iter.get_next(datetime)
    while next_run <= end_date:
        count += 1
        next_run = run_iter.get_next(datetime)
    return count

