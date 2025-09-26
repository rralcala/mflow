import os
import sys
import argparse
from datetime import datetime

from commands.cash_flow_detail import handle_cash_flow_detail
from commands.cash_flow import handle_cash_flow
from lib.config import DATE_FORMAT_STRING

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(script_dir, "..")
sys.path.insert(0, project_root)

parser = argparse.ArgumentParser(description="Money flow cli!")
subparsers = parser.add_subparsers(
    dest="command", required=True, help="Available commands"
)

cash_flow_detail_parser = subparsers.add_parser("cash-flow-detail", help="Daily cash flow detail")
cash_flow_detail_parser.add_argument(
    "-d", "--debug", action="store_true", help="Debug logging."
)
cash_flow_detail_parser.set_defaults(func=handle_cash_flow_detail)

cash_flow_parser = subparsers.add_parser("cash-flow", help="Monthly cash flow")
cash_flow_parser.add_argument("-p", "--plot", action="store_true", help="Create chart.")
cash_flow_parser.add_argument("-d", "--debug", action="store_true", help="Debug logging.")
cash_flow_parser.add_argument(
    "-s",
    "--date",
    type=str,
    default=datetime.today().strftime(DATE_FORMAT_STRING),
    help=f"Start date in {DATE_FORMAT_STRING} format.",
)
cash_flow_parser.set_defaults(func=handle_cash_flow)

args = parser.parse_args()

if hasattr(args, "func"):
    args.func(args)
else:
    parser.print_help()
