"""
Command line interface entrypoint for money flow application.
"""

import argparse
import os
import sys
from datetime import datetime

from commands.asset_summary import handle_asset_summary
from commands.cash_flow import handle_cash_flow
from commands.cash_flow_detail import handle_cash_flow_detail
from lib.config import DATE_FORMAT_STRING

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(script_dir, "..")
sys.path.insert(0, project_root)

def clear_cached_data(args):
    """Clear cache on gRPC server."""
    from grpc_client.cash_flow_client import clear_cache as clear_cache

    print(clear_cache().success)

parser = argparse.ArgumentParser(description="Money flow cli!")
subparsers = parser.add_subparsers(
    dest="command", required=True, help="Available commands"
)

cash_flow_detail_parser = subparsers.add_parser(
    "cash-flow-detail", help="Daily cash flow detail"
)
cash_flow_detail_parser.add_argument(
    "-d", "--debug", action="store_true", help="Debug logging."
)
cash_flow_detail_parser.add_argument("-c", "--csv", action="store_true", help="In CSV format.")
cash_flow_detail_parser.set_defaults(func=handle_cash_flow_detail)

cash_flow_parser = subparsers.add_parser("cash-flow", help="Monthly cash flow")

cash_flow_parser.add_argument(
    "-d", "--debug", action="store_true", help="Debug logging."
)
cash_flow_parser.add_argument(
    "-s",
    "--date",
    type=str,
    default=datetime.today().strftime(DATE_FORMAT_STRING),
    help=f"Start date in {DATE_FORMAT_STRING} format.",
)
cash_flow_parser.set_defaults(func=handle_cash_flow)

asset_summary_parser = subparsers.add_parser("asset-summary", help="Asset summary")
asset_summary_parser.add_argument(
    "-p", "--print-pos", action="store_true", help="Create chart."
)
asset_summary_parser.add_argument(
    "-d", "--debug", action="store_true", help="Create chart."
)
asset_summary_parser.add_argument(
    "-n", "--print-neg", action="store_true", help="Create chart."
)
asset_summary_parser.add_argument(
    "-c", "--check-history", action="store_true", help="Create chart."
)
asset_summary_parser.set_defaults(func=handle_asset_summary)

clear_cache_parser = subparsers.add_parser("clear-cache", help="Clear cached data")
clear_cache_parser.set_defaults(func=clear_cached_data)

args = parser.parse_args()

if hasattr(args, "func"):
    args.func(args)
else:
    parser.print_help()
