import os
import sys
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(script_dir, '..')
sys.path.insert(0, project_root)

import argparse
import logging

from reports.list_assets import list_assets
from lib.util import config_logging

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate cash flow.")
    parser.add_argument("-p", "--print-pos", action="store_true", help="Create chart.")
    parser.add_argument("-d", "--debug", action="store_true", help="Create chart.")
    parser.add_argument("-n", "--print-neg", action="store_true", help="Create chart.")
    parser.add_argument(
        "-c", "--check-history", action="store_true", help="Create chart."
    )
    args = parser.parse_args()

    config_logging(args.debug)

    tpval, tnval, returns = list_assets(args.print_pos, args.print_neg)

    ret = 0.0
    grand_total = tpval + tnval
    for current_value, current_return, _ in returns:
        tret = (current_value / grand_total) * current_return
        ret += tret
    logging.info(
    f"Total positive value: {tpval:,.2f} USD, Total negative value: {tnval:,.2f} USD"
)
    logging.info(
    f"Total portfolio value: {grand_total:,.2f} USD {ret*100:,.2f}% annualized return"
)