from croniter import croniter
from datetime import datetime, timedelta

FORMAT_STRING = "%m/%d/%Y"
USDPYG = 7400

def count_cron_runs(cron_pattern: str, start_date: str, end_date: str) -> int:
    """
    Counts how many times a cron pattern runs between two dates.
    """
    start = datetime.strptime(start_date, FORMAT_STRING) - timedelta(days=1)
    end = datetime.strptime(end_date, FORMAT_STRING)
    run_iter = croniter(cron_pattern, start)
    count = 0
    next_run = run_iter.get_next(datetime)
    while next_run <= end:
        count += 1
        next_run = run_iter.get_next(datetime)
    return count
