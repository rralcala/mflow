import os
import sys
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(script_dir, '..')
sys.path.insert(0, project_root)

import argparse
import logging

import matplotlib.pyplot as plt

from reports.cash_flow import cash_flow
from lib.util import config_logging

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Calculate cash flow.")
    parser.add_argument("-p", "--plot", action="store_true", help="Create chart.")
    parser.add_argument("-d", "--debug", action="store_true", help="Debug logging.")
    parser.add_argument(
        "-s",
        "--date",
        type=str,
        default="09/01/2025",
        help='Start date in "MM/DD/YYYY" format.',
    )
    args = parser.parse_args()

    config_logging(args.debug)

    x, y, t = cash_flow()

    for i, xv in enumerate(x):
        print(f"{xv}: {y[i]:,.0f}USD {t[i][0]:,.0f}USD {t[i][1]:,.0f}PYG")
    min_value = min(y)
    min_index = y.index(min_value)
    logging.info(f"Minimum value: {min_value:,.2f} USD in {x[min_index]}")

    if args.plot:
        plt.plot(x, y)
        plt.xticks(rotation=90)
        plt.hlines(y=0, xmin=x[0], xmax=x[-1], colors="red", linestyles="dashed")
        plt.xlabel("Month")
        plt.ylabel("Dollar Balance")
        plt.title("Cash Flow Over Time")
        plt.show()