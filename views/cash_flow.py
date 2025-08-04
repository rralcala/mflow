from datetime import datetime, timedelta, timezone

from flask_login import current_user

from data.exchange_rates import ExchangeRates
from lib.user_config import UserStore
from reports.cash_flow import generate_timeline


def cash_flow(assets):
    secondary_currency = UserStore.get_user_config(current_user.id).SECONDARY_CURRENCY
    sec_currency_contry = f"{secondary_currency}-PY"

    end_dt = datetime.now() + timedelta(days=365)
    today_str = datetime.now().strftime("%Y-%m-%d")
    payments = []
    for country, id, tl in generate_timeline(assets, end_dt):
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
        timeline.setdefault(key, {"USD-US": uu, "USD-PY": up, sec_currency_contry: pp})
        timeline[key][f"{payment['currency']}-{payment['country']}"] += payment[
            "amount"
        ]
        uu = timeline[key]["USD-US"]
        up = timeline[key]["USD-PY"]
        pp = timeline[key][sec_currency_contry]
    tl_list = []
    tl_dates = sorted(timeline.keys())
    for date in tl_dates:
        tl_list.append((date, timeline[date]))
    min_val = {
        "USD-US": 200000000.0,
        "USD-PY": 200000000.0,
        sec_currency_contry: 200000000.0,
    }

    min_date = {
        "USD-US": today_str,
        "USD-PY": today_str,
        sec_currency_contry: today_str,
    }
    result = []
    for date, amounts in tl_list:
        tl = (
            amounts["USD-US"]
            + amounts["USD-PY"]
            + amounts[sec_currency_contry]
            / ExchangeRates.exchange_rate("USD" + secondary_currency)
        )

        # Past dates are only stale payments.
        for key, amount in amounts.items():
            if amount < min_val[key] and date >= today_str:
                min_val[key] = amount
                min_date[key] = date
        result.append(
            {
                "date": date,
                "USD-US": amounts["USD-US"],
                "USD-PY": amounts["USD-PY"],
                sec_currency_contry: amounts[sec_currency_contry],
                "Total": tl,
            }
        )
        # output.write(
        #    f"<tr><td>{date}</td><td style=\"text-align: right;\">{amounts['USD-US']:,.0f}</td><td style=\"text-align: right;\">{amounts['USD-PY']:,.0f}</td><td style=\"text-align: right;\">{sec_currency_contry_amount}</td><td style=\"text-align: right;\">{tl:,.0f}</td></tr>\n"
        # )
    # output.write("</table>")
    # delta = relativedelta(
    #    datetime.strptime(min_date[sec_currency_contry], "%Y-%m-%d"), datetime.today()
    # )
    # months_till = delta.months + delta.years * 12
    # if months_till <= 0:
    #    months_till = 1
    # response = ""
    # for key, amount in min_val.items():
    #    response += f"<p><b>{key}</b><br/>Min: {amount:,.0f} on {min_date[key]}"
    #    if key == sec_currency_contry and months_till > 0:
    #        response += f" in {months_till} months. Could spend: {amount/months_till:,.0f}/Mo<br/>"
    #    else:
    #        response += "<br/>"
    #    if len(tl_list) > 1:
    #        response += f"Last: {tl_list[-1][1][key]:,.0f} Delta: {(tl_list[-1][1][key] - tl_list[0][1][key]):,.0f}</p>"

    return result
