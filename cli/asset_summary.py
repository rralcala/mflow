import os
import sys
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(script_dir, '..')
sys.path.insert(0, project_root)

import argparse
import logging

from reports.list_assets import list_assets

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate cash flow.")
    parser.add_argument("-p", "--print-pos", action="store_true", help="Create chart.")
    parser.add_argument("-d", "--debug", action="store_true", help="Create chart.")
    parser.add_argument("-n", "--print-neg", action="store_true", help="Create chart.")
    parser.add_argument(
        "-c", "--check-history", action="store_true", help="Create chart."
    )
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    logging.getLogger("urllib3").setLevel(logging.WARNING)

    list_assets(args.print_pos, args.print_neg)