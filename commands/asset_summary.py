import csv
import logging
import sys

from grpc_client.cash_flow_client import fetch_list_assets
from lib.util import config_logging


def handle_asset_summary(args):
    config_logging(args.debug)

    summary, returns, breakdown = fetch_list_assets(args.print_pos, args.print_neg)

    ret = 0.0
    tpval = 0.0
    tnval = 0.0
    for _, pval, nval in summary:
        tpval += pval
        tnval += nval

    grand_total = tpval + tnval
    for current_value, current_return, _ in returns:
        tret = (current_value / grand_total) * current_return
        ret += tret
    writer = csv.writer(
        sys.stdout, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL
    )
    for v in breakdown.values():
        if len(v) > 0:
            for row in v:
                amount, currency = row[1].split(" ")
                writer.writerow([row[0], amount, currency])

    logging.info(
        f"Total positive value : {tpval:,.2f} USD ({(tnval/tpval*-100):,.2f}% Debt to Assets)"
    )
    logging.info(f"Total negative value : {tnval:,.2f} USD")
    logging.info(
        f"Total portfolio value: {grand_total:,.2f} USD ({ret*100:,.2f}% ARoI)"
    )
