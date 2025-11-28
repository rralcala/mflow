import logging
from pprint import pprint
from datetime import datetime

from lib.util import config_logging
from data.sqlite import save_summary
from reports.list_assets import list_assets


def handle_asset_summary(args):
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
        f"Total positive value : {tpval:,.2f} USD ({(tnval/tpval*-100):,.2f}% Debt to Assets)"
    )
    logging.info(f"Total negative value : {tnval:,.2f} USD")
    logging.info(
        f"Total portfolio value: {grand_total:,.2f} USD ({ret*100:,.2f}% ARoI)"
    )
    save_summary(datetime.now().strftime("%Y-%m-%d"), f"{grand_total:.2f}")
