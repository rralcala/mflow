import os
import sys
import argparse
import logging

from commands.cash_flow_detail import handle_cash_flow_detail

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(script_dir, "..")
sys.path.insert(0, project_root)

parser = argparse.ArgumentParser(description="Money flow cli!")
subparsers = parser.add_subparsers(
    dest="command", required=True, help="Available commands"
)

cash_flow_detail_parser = subparsers.add_parser("cash-flow-detail", help="Add an item")
cash_flow_detail_parser.add_argument(
    "-d", "--debug", action="store_true", help="Debug logging."
)
cash_flow_detail_parser.set_defaults(func=handle_cash_flow_detail)

args = parser.parse_args()

if hasattr(args, "func"):
    args.func(args)
else:
    parser.print_help()
