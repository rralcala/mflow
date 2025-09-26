import os
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(script_dir, "..")
sys.path.insert(0, project_root)

import argparse

from reports.cash_flow import cash_flow
from lib.util import config_logging
from data.db import Transactions

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Calculate cash flow.")
    parser.add_argument(
        "-a", "--account", type=str, help="Create chart.", required=True
    )
    parser.add_argument("-y", "--year", type=str, help="Create chart.", required=False)
    parser.add_argument("-m", "--month", type=str, help="Create chart.", required=False)
    parser.add_argument("-c", "--amount", type=str, help="Create chart.", required=True)
    parser.add_argument(
        "-e", "--description", type=str, help="Create chart.", required=True
    )
    parser.add_argument("-d", "--debug", action="store_true", help="Debug logging.")

    args = parser.parse_args()

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
