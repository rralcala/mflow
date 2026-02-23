import io
from datetime import datetime, timedelta, timezone
import logging

from flask import make_response
from lib.util import PRINTER
from data.internal import exchange_rate
from reports.cash_flow import generate_timeline

# Split current balances and upcoming payments.
def upcoming_payments(assets):
    end_dt = datetime.now() + timedelta(days=31)
    payments = []
    output = io.StringIO()
    for country, tl in generate_timeline(assets, end_dt):
        for entry in tl:
            #output.write(PRINTER.pformat(tl)+"\n")
            d, (amount, currency) = entry
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
            if amount <= 0.0:
                continue
            payments.append(payment)

    payments = sorted(payments, key=lambda x: (x["country"], x["date"]))
    
    cur_month = str(datetime.now().month).zfill(2)
    output.write(f"{payment['country']}\n\n")
    output.write("Country,Date:     Amount CUR\n")
    for payment in payments:
        output.write(
            f"{payment['date']}: {payment['amount']:12,.0f} {payment['currency']}\n"
        )
        pmonth = payment["date"].split("-")[1]
        #logging.warning(f"pmonth: {pmonth}, cur_month: {cur_month}")
        if pmonth != str(cur_month):
            output.write(f"\n{payment['country']}\n\n")
            output.write("Country,Date:     Amount CUR\n")
            cur_month = pmonth
    #response = make_response(output.getvalue(), 200)
    '''timeline = {}
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
    output.write("</table>")'''
    response = make_response(output.getvalue(), 200)
    response.mimetype = "text/plain"
    return response
