import os
import sys
import argparse
from datetime import datetime

from commands.cash_flow_detail import handle_cash_flow_detail
from commands.cash_flow import handle_cash_flow
from commands.asset_summary import handle_asset_summary
from commands.check_history import handle_check_history
from commands.create_transaction import handle_create_transaction
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

asset_summary_parser = subparsers.add_parser("asset-summary", help="Asset summary")
asset_summary_parser.add_argument("-p", "--print-pos", action="store_true", help="Create chart.")
asset_summary_parser.add_argument("-d", "--debug", action="store_true", help="Create chart.")
asset_summary_parser.add_argument("-n", "--print-neg", action="store_true", help="Create chart.")
asset_summary_parser.add_argument(
    "-c", "--check-history", action="store_true", help="Create chart."
)
asset_summary_parser.set_defaults(func=handle_asset_summary)

check_history_parser = subparsers.add_parser("check-history", help="Check performance history")
check_history_parser.add_argument("-d", "--debug", action="store_true", help="Debug logging.")
check_history_parser.add_argument("-p", "--plot", action="store_true", help="Create chart.")
check_history_parser.set_defaults(func=handle_check_history)

create_transaction_parser = subparsers.add_parser("create-transaction", help="Create transaction")
create_transaction_parser.add_argument(
    "-a", "--account", type=str, help="Create chart.", required=True
)
create_transaction_parser.add_argument("-y", "--year", type=str, help="Create chart.", required=False)
create_transaction_parser.add_argument("-m", "--month", type=str, help="Create chart.", required=False)
create_transaction_parser.add_argument("-c", "--amount", type=str, help="Create chart.", required=True)
create_transaction_parser.add_argument(
    "-e", "--description", type=str, help="Create chart.", required=True
)
create_transaction_parser.add_argument("-d", "--debug", action="store_true", help="Debug logging.")
create_transaction_parser.set_defaults(func=handle_create_transaction)

args = parser.parse_args()

if hasattr(args, "func"):
    args.func(args)
else:
    parser.print_help()
