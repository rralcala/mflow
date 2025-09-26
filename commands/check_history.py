import matplotlib.pyplot as plt

from reports.list_assets import check_history, list_assets
from lib.util import config_logging

def handle_check_history(args):
    config_logging(args.debug)

    asset_data = list_assets(False, False)
    tpval = 0.0
    tnval = 0.0
    for currency, pval, nval in asset_data["currency_summary"]:
        tpval += pval
        tnval += nval
    x, y = check_history(tpval, tnval)
    if args.plot:
        plt.plot(x, y)
        plt.xticks(rotation=90)
        plt.hlines(y=0, xmin=x[0], xmax=x[-1], colors="red", linestyles="dashed")
        plt.xlabel("Month")
        plt.ylabel("Dollar Savings")
        plt.title(f"Asset Value Change History {(tpval + tnval):,.0f}")
        plt.show()
