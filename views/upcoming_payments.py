import logging
from datetime import datetime, timezone

from dateutil.relativedelta import relativedelta

from lib.util import PRINTER
from reports.cash_flow import generate_timeline


def upcoming_payments_data(assets, exclude_capital=False):
    first_day_current_month = datetime.now().replace(day=1)
    end_dt = first_day_current_month + relativedelta(months=2) - relativedelta(days=1)
    payments_by_month = {}

    for country, asset_id, timeline in generate_timeline(assets, end_dt):
        for entry in timeline:
            try:
                d, (amount, currency, is_capital) = entry
            except ValueError as e:
                logging.error(PRINTER.pformat(entry))
                raise e
            dt = datetime(d.year, d.month, d.day)
            if dt.tzinfo is None:
                dt_aware = dt.replace(tzinfo=timezone.utc)
            else:
                dt_aware = dt.astimezone(timezone.utc)
            if exclude_capital and is_capital:
                continue
            if amount <= 0.0:
                continue
            payment = {
                "assetId": asset_id,
                "country": country,
                "date": dt_aware.strftime("%Y-%m-%d"),
                "amount": amount,
                "currency": currency,
                "capital": is_capital,
            }

            month_key = dt_aware.strftime("%Y-%m")
            payments_by_month.setdefault(month_key, {})
            payments_by_month[month_key].setdefault(country, [])
            payments_by_month[month_key][country].append(payment)

    sorted_payments = {}
    for month_key in sorted(payments_by_month):
        sorted_payments[month_key] = {}
        for country in sorted(payments_by_month[month_key]):
            sorted_payments[month_key][country] = sorted(
                payments_by_month[month_key][country],
                key=lambda payment: payment["date"],
            )

    return sorted_payments


def upcoming_payments_flat(assets, exclude_capital=False):
    payments_by_month = upcoming_payments_data(assets, exclude_capital)
    flat_payments = []
    fake_id = 0
    for month_key in sorted(payments_by_month):
        for country in sorted(payments_by_month[month_key]):
            for payment in payments_by_month[month_key][country]:
                payment["id"] = payment["assetId"] + "-" + payment["date"]
                fake_id += 1

                flat_payments.append(payment)
    return flat_payments
