import os
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(script_dir, "..")
sys.path.insert(0, project_root)

import argparse
import logging
from pprint import pprint

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

    asset_data = list_assets(args.print_pos, args.print_neg)

    ret = 0.0
    tpval = 0.0
    tnval = 0.0
    for _, pval, nval in asset_data["currency_summary"]:
        tpval += pval
        tnval += nval

    grand_total = tpval + tnval
    for current_value, current_return, _ in asset_data["return_history"]:
        tret = (current_value / grand_total) * current_return
        ret += tret
    asset_data["return_history"] = []
    pprint(asset_data)
    logging.info(
        f"Total positive value: {tpval:,.2f} USD, Total negative value: {tnval:,.2f} USD"
    )
    logging.info(
        f"Total portfolio value: {grand_total:,.2f} USD {ret*100:,.2f}% annualized return"
    )
