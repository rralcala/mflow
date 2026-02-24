import io
from datetime import datetime, timedelta, timezone

from flask import make_response

from data.internal import exchange_rate
from reports.cash_flow import generate_timeline


def cash_flow(assets):
    end_dt = datetime.now() + timedelta(days=365)
    payments = []
    for country, tl in generate_timeline(assets, end_dt):
        for entry in tl:
            d, (amount, currency, _) = entry
            dt = datetime(d.year, d.month, d.day)
            if dt.tzinfo is None:
                dt_aware = dt.replace(tzinfo=timezone.utc)
            else:
                dt_aware = dt.astimezone(timezone.utc)
            payment = {
                "country": country,
                "date": dt_aware.strftime("%Y-%m-%d"),
                "amount": amount,
                "currency": currency,
            }
            payments.append(payment)

    timeline = {}
    payments = sorted(payments, key=lambda x: (x["date"], x["country"]))
    uu = 0.0
    up = 0.0
    pp = 0.0
    for payment in payments:
        key = payment["date"]
        timeline.setdefault(key, {"USD-US": uu, "USD-PY": up, "PYG-PY": pp})
        timeline[key][f"{payment['currency']}-{payment['country']}"] += payment[
            "amount"
        ]
        uu = timeline[key]["USD-US"]
        up = timeline[key]["USD-PY"]
        pp = timeline[key]["PYG-PY"]

    output = io.StringIO()
    output.write(
        f'<table><tr><th>Date</th><th style="text-align: right;">USD-US</th><th style="text-align: right;">USD-PY</th><th style="text-align: right;">PYG-PY</th><th style="text-align: right;">Total</th></tr>\n'
    )
    for date, amounts in timeline.items():
        tl = (
            amounts["USD-US"]
            + amounts["USD-PY"]
            + amounts["PYG-PY"] / exchange_rate("USDPYG")
        )
        if amounts["PYG-PY"] > 0.0:
            pyg_py_val = f"{amounts['PYG-PY']:,.2f}"
        else:
            pyg_py_val = f"<p style=\"color:red;\"><b>{amounts['PYG-PY']:,.2f}</b></p>"
        output.write(
            f"<tr><td>{date}</td><td style=\"text-align: right;\">{amounts['USD-US']:,.2f}</td><td style=\"text-align: right;\">{amounts['USD-PY']:,.2f}</td><td style=\"text-align: right;\">{pyg_py_val}</td><td style=\"text-align: right;\">{tl:,.2f}</td></tr>\n"
        )
    output.write("</table>")
    response = make_response(output.getvalue(), 200)
    response.mimetype = "text/html"
    return response
