import os
import sys
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(script_dir, '..')
sys.path.insert(0, project_root)

import argparse
import logging

import matplotlib.pyplot as plt

from reports.cash_flow import cash_flow

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Calculate cash flow.")
    parser.add_argument("-p", "--plot", action="store_true", help="Create chart.")
    parser.add_argument(
        "-d",
        "--date",
        type=str,
        default="09/01/2025",
        help='Start date in "MM/DD/YYYY" format.',
    )
    args = parser.parse_args()

    x, y = cash_flow()

    if args.plot:
        logging.info("Plotting Cash Flow Over Time.")
        plt.plot(x, y)
        plt.xticks(rotation=90)
        plt.hlines(y=0, xmin=x[0], xmax=x[-1], colors="red", linestyles="dashed")
        plt.xlabel("Month")
        plt.ylabel("Dollar Balance")
        plt.title("Cash Flow Over Time")
        plt.show()