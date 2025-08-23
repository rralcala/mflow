import os
import sys
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(script_dir, '..')
sys.path.insert(0, project_root)

import argparse

import matplotlib.pyplot as plt

from reports.list_assets import check_history, list_assets
from lib.util import config_logging

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate cash flow.")
    parser.add_argument("-d", "--debug", action="store_true", help="Debug logging.")
    parser.add_argument("-p", "--plot", action="store_true", help="Create chart.")
    args = parser.parse_args()

    config_logging(args.debug)

    tpval, tnval = list_assets(False, False)
    x, y = check_history(tpval, tnval)
    if args.plot:
        plt.plot(x, y)
        plt.xticks(rotation=90)
        plt.hlines(y=0, xmin=x[0], xmax=x[-1], colors="red", linestyles="dashed")
        plt.xlabel("Month")
        plt.ylabel("Dollar Savings")
        plt.title(f"Asset Value Change History {(tpval + tnval):,.0f}")
        plt.show()
