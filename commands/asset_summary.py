import logging
from datetime import datetime
from pprint import pprint

from data.sqlite import read_history, save_summary
from lib.util import config_logging
from reports.list_assets import list_assets


def handle_asset_summary(args):
    config_logging(args.debug)

    summary, returns, breakdown = list_assets(args.print_pos, args.print_neg)

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

    pprint(breakdown)

    logging.info(
        f"Total positive value : {tpval:,.2f} USD ({(tnval/tpval*-100):,.2f}% Debt to Assets)"
    )
    logging.info(f"Total negative value : {tnval:,.2f} USD")
    logging.info(
        f"Total portfolio value: {grand_total:,.2f} USD ({ret*100:,.2f}% ARoI)"
    )
    save_summary(datetime.now().strftime("%Y-%m-01"), f"{grand_total:.2f}")
    history = read_history(2)
    logging.info(
        f"Monthly change: {float(history[0][1]) - float(history[1][1]):,.2f} USD"
    )
