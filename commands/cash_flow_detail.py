import logging
from datetime import datetime, timedelta

from mflow_shared_rralcala.data.internal import exchange_rate

from grpc_client.cash_flow_client import fetch_timeline
from lib.util import config_logging


def handle_cash_flow_detail(args):
    config_logging(args.debug)
    end = datetime.today() + timedelta(days=365)
    col = {
        "US": {"USD": 0},
        "PY": {"USD": 1, "PYG": 2},
    }
    timeline = {}
    upcoming = []
    # Fetch timeline from gRPC server instead of local function
    for instrument in fetch_timeline(end):
        upcoming += instrument[1]
        for payments in instrument[1]:
            key = payments[0]
            timeline.setdefault(key, [0.0, 0.0, 0.0])
            timeline[key][col[instrument[0]][payments[1][1]]] += payments[1][0]
    per_date = {}
    upcoming = list(sorted(upcoming, key=lambda x: x[0]))
    for item in upcoming:
        per_date.setdefault(item[0], [])
        per_date[item[0]].append(item[1])
    dates = list(sorted(timeline.keys()))
    uu, pu, pp = 0, 0, 0
    min_pu = 0
    min_pp = 0
    for date in dates:
        uu += timeline[date][0]
        pu += timeline[date][1]
        pp += timeline[date][2]
        ppu = pp / exchange_rate("USDPYG")
        if pu < min_pu:
            min_pu = pu
        if pp < min_pp:
            min_pp = pp
        if args.csv:
            print(f"{date:%Y-%m-%d},{uu:.0f},{pu:.0f},{pp:.0f},{ppu:.0f}")
        else:
            print(
                f"{date:%Y-%m-%d}: {uu:10,.0f}USD {pu:10,.0f}USD {pp:15,.0f}PYG/[{ppu:10,.0f}USD] {uu+pu+ppu:10,.0f}USD"
            )

        logging.debug(per_date[date])
    if not args.csv:
        logging.info(f"Min PY USD: {min_pu:10,.0f}USD")
        logging.info(f"Min PY PYG: {min_pp:10,.0f}PYG")
