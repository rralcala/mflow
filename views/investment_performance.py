from reports.list_assets import list_asset_performance


def render_details(items):
    ret = "<table>"
    ret += '<tr><th>Asset</th><th style="text-align: right;">Amount</th><th>Currency</th><th style="text-align: right;">Rate</th></tr>'
    for item in items:
        ret += f'<tr><td>{item[0]}</td><td style="text-align: right;">{item[1]:,.0f}</td><td>{item[2]}</td><td style="text-align: right;">{item[3]:.2f}%</td></tr>'
    ret += "</table>"
    return ret


def investment_performance(assets):
    performance = list_asset_performance(assets)
    sum_value = 0.0
    z_vol = 0.0
    n_vol = 0.0
    nz_vol = 0.0
    over_7_sum = 0.0
    n_assets = []
    z_assets = []
    nz_assets = []
    over_7_percent = []
    for item in performance:

        sum_value += item[1]
        if item[3] < 0.0:
            n_vol += item[1]
            n_assets.append(item)
        elif item[3] == 0.0:
            z_vol += item[1]
            z_assets.append(item)
        elif item[3] > 7.0:
            over_7_percent.append(item)
            over_7_sum += item[1]
        else:
            nz_vol += item[1]
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
