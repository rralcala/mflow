import logging
from datetime import datetime

from lib.config import DATE_FORMAT_STRING
from lib.util import config_logging
from reports.cash_flow import cash_flow


def handle_cash_flow(args):
    config_logging(args.debug)
    start = datetime.strptime(args.date, DATE_FORMAT_STRING)
    logging.info(start)
    x, balances, t = cash_flow(start)
    print("Date:   \tBalance USD, Income USD, Income PYG")
    for i, xv in enumerate(x):
        print(f"{xv}:\t{balances[i]:,.0f}USD {t[i][0]:,.0f}USD {t[i][1]:,.0f}PYG")
    min_value = min(balances)
    min_index = balances.index(min_value)
    logging.info(f"Minimum value: {min_value:,.2f} USD in {x[min_index]}")
