from reports.list_assets import list_asset_performance


def investment_performance(assets):
    performance = list_asset_performance(assets)
    n_assets = []
    z_assets = []
    nz_assets = []
    over_7_percent = []
    for item in performance:
        if item[3] < 0.0:
            n_assets.append(item)
        elif item[3] == 0.0:
            z_assets.append(item)
        elif item[3] > 7.0:
            over_7_percent.append(item)
        else:
            nz_assets.append(item)
    response = [
        {"to": 0.0, "assets": sorted(n_assets, key=lambda x: x[1], reverse=True)},
        {
            "from": 0.0,
            "to": 0.0,
            "assets": sorted(z_assets, key=lambda x: x[1], reverse=True),
        },
        {
            "from": 0.0,
            "to": 7.0,
            "assets": sorted(nz_assets, key=lambda x: x[1], reverse=True),
        },
        {
            "from": 7.0,
            "assets": sorted(over_7_percent, key=lambda x: x[1], reverse=True),
        },
    ]

    return response
