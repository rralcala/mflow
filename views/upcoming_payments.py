import io
import logging
from datetime import datetime, timedelta, timezone

from flask import make_response

from lib.util import PRINTER
from reports.cash_flow import generate_timeline


# Split current balances and upcoming payments.
def upcoming_payments(assets, exclude_capital=False):
    end_dt = datetime.now() + timedelta(days=31)
    payments = []
    output = io.StringIO()
    for country, tl in generate_timeline(assets, end_dt):
        for entry in tl:
            try:
                d, (amount, currency, is_capital) = entry
            except ValueError as e:
                logging.warning(PRINTER.pformat(entry))
                raise e
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
                "capital": is_capital,
            }
            if amount <= 0.0:
                continue
            payments.append(payment)

    payments = sorted(payments, key=lambda x: (x["country"], x["date"]))

    cur_month = str(datetime.now().month).zfill(2)

    output.write(f"[{payment['country']}] Date:     Amount CUR\n")
    for payment in payments:
        pmonth = payment["date"].split("-")[1]
        # logging.warning(f"pmonth: {pmonth}, cur_month: {cur_month}")
        if pmonth != str(cur_month):
            output.write(f"\n\n")
            output.write(f"[{payment['country']}] Date:     Amount CUR\n")
            cur_month = pmonth
        if exclude_capital and payment["capital"]:
            continue
        output.write(
            f"{payment['date']}: {payment['amount']:12,.0f} {payment['currency']} {'(Capital)' if payment['capital'] else ''}\n"
        )

    response = make_response(output.getvalue(), 200)
    response.mimetype = "text/plain"
    return response
