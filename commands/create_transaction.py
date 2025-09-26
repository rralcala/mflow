from reports.cash_flow import cash_flow
from lib.util import config_logging
from data.db import Transactions

def handle_create_transaction(args):
    config_logging(args.debug)
    t = Transactions()
    if not args.year:
        t.set(
            args.account,
            "",
            "",
            {"amount": float(args.amount), "description": args.description},
        )
        print(t.get(args.account, "", ""))
    else:
        t.set(
            args.account,
            args.year,
            args.month,
            {"amount": float(args.amount), "description": args.description},
        )
        print(t.get(args.account, args.year, args.month))
