from datetime import datetime, timedelta

from data.internal import exchange_rate
from lib.util import config_logging
from reports.cash_flow import generate_timeline


def handle_cash_flow_detail(args):
    config_logging(args.debug)
    end = datetime.today() + timedelta(days=180)
    col = {
        "US": {"USD": 0},
        "PY": {"USD": 1, "PYG": 2},
    }
    timeline = {}
    for instrument in generate_timeline(end):
        # countries.setdefault(instrument[0], {})
        for payments in instrument[1]:
            key = payments[0]
            timeline.setdefault(key, [0.0, 0.0, 0.0])
            timeline[key][col[instrument[0]][payments[1][1]]] += payments[1][0]
    dates = list(sorted(timeline.keys()))
    uu, pu, pp = 0, 0, 0
    for date in dates:
        uu += timeline[date][0]
        pu += timeline[date][1]
        pp += timeline[date][2]
        ppu = pp / exchange_rate("USDPYG")
        print(
            f"{date}: {uu:10,.2f}USD {pu:10,.0f}USD {pp:15,.0f}PYG ({ppu:10,.0f}USD) {uu+pu+ppu:10,.0f}USD"
        )
