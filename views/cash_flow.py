from datetime import datetime, timedelta, timezone

from flask_login import current_user

from data.exchange_rates import ExchangeRates
from lib.logger import get_logger
from lib.user_config import UserStore
from reports.cash_flow import generate_timeline

Logger = get_logger()


def cash_flow(assets):

    secondary_currency = UserStore.get_user_config(current_user.id).SECONDARY_CURRENCY
    secondary_country = UserStore.get_user_config(current_user.id).SECONDARY_COUNTRY
    sec_currency_contry = f"{secondary_currency}-{secondary_country}"
    pri_currency_sec_contry = "USD-" + secondary_country
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
                "id": id,
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
    report_for = set(["USD-US", pri_currency_sec_contry, sec_currency_contry])
    for payment in payments:
        currency_country = f"{payment['currency']}-{payment['country']}"
        if currency_country not in report_for:
            continue
        key = payment["date"]
        timeline.setdefault(
            key, {"USD-US": uu, pri_currency_sec_contry: up, sec_currency_contry: pp}
        )
        timeline[key][currency_country] += payment["amount"]
        uu = timeline[key]["USD-US"]
        up = timeline[key][pri_currency_sec_contry]
        pp = timeline[key][sec_currency_contry]
    tl_list = []
    tl_dates = sorted(timeline.keys())
    for date in tl_dates:
        tl_list.append((date, timeline[date]))
    min_val = {
        "USD-US": tl_list[0][1]["USD-US"],
        pri_currency_sec_contry: tl_list[0][1][pri_currency_sec_contry],
        sec_currency_contry: tl_list[0][1][sec_currency_contry],
    }

    min_date = {
        "USD-US": today_str,
        pri_currency_sec_contry: today_str,
        sec_currency_contry: today_str,
    }
    result = []
    for date, amounts in tl_list:
        tl = (
            amounts["USD-US"]
            + amounts[pri_currency_sec_contry]
            + amounts[sec_currency_contry]
            / ExchangeRates.exchange_rate("USD" + secondary_currency)
        )

        # Past dates are only stale payments.
        for key, amount in amounts.items():
            if amount < min_val[key] and date >= today_str:
                min_val[key] = amount
                min_date[key] = date
        if tl == 0.0:
            continue
        result.append(
            {
                "date": date,
                "USD-US": amounts["USD-US"],
                pri_currency_sec_contry: amounts[pri_currency_sec_contry],
                sec_currency_contry: amounts[sec_currency_contry],
                "Total": tl,
            }
        )

    return result
