from flask import make_response

from asset_classes.fetcher import fetch_assets
from data.asset_store import load_assets
from lib import config, util
from reports.list_assets import list_asset_performance

import service

# register the route using the shared Flask application
def investment_performance():
    # use the ASSETS variable living in the service module so that all views
    # operate on the same cache
    if not service.ASSETS:
        service.ASSETS = load_assets(fetch_assets, config.BASE_PATH, "key.json")
        service.append_cb(service.ASSETS)

    performance = list_asset_performance(service.ASSETS)
    sum_value = 0.0
    z_vol = 0.0
    nz_vol = 0.0
    over_7_sum = 0.0
    z_assets = []
    nz_assets = []
    over_7_percent = []
    for item in performance:
        sum_value += item[1]
        if item[3] == 0.0:
            z_vol += item[1]
            z_assets.append(item)
        elif item[3] > 7.0:
            over_7_percent.append(item)
            over_7_sum += item[1]
        else:
            nz_vol += item[1]
            nz_assets.append(item)
    z_assets = sorted(z_assets, key=lambda x: x[1], reverse=True)
    over_7_percent = sorted(over_7_percent, key=lambda x: x[1], reverse=True)
    nz_assets = sorted(nz_assets, key=lambda x: x[1], reverse=True)
    response = make_response(
        f"Total: ${sum_value:,.0f}\n\n"
        + util.PRINTER.pformat(z_assets)
        + f"\n\nZero % Capital: ${z_vol:,.0f} ({z_vol/sum_value*100:,.2f}%)\n\n"
        + util.PRINTER.pformat(nz_assets)
        + f"\n\nUnder 7%: ${nz_vol:,.0f} ({nz_vol/sum_value*100:,.2f}%)\n\n"
        + util.PRINTER.pformat(over_7_percent)
        + f"\n\nOver 7% Capital: ${over_7_sum:,.0f} ({over_7_sum/sum_value*100:,.2f}%)",
        200,
    )
    response.mimetype = "text/plain"
    return response
