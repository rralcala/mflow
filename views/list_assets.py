from flask import make_response

from data.internal import exchange_rate
from lib.util import PRINTER
from reports.list_assets import NEGATIVES, POSITIVES
from reports.list_assets import list_assets as r_list_assets


def list_assets(assets):
    a, b, c = r_list_assets(assets, print_pos=True, print_neg=True)

    sum = 0.0
    for item in a:
        sum += item[1] + item[2]

    grand_total = sum
    ret = 0.0
    sum_py = 0.0
    sum_us = 0.0
    for current_value, current_return, _, country in b:
        tret = (current_value / grand_total) * current_return
        ret += tret
        if country == "PY":
            sum_py += current_value
        else:
            sum_us += current_value
    debt = 0.0
    capital = 0.0

    for item in c[POSITIVES]:

        amount_str, currency = item[1].split(" ")
        amount = float(amount_str.replace(",", ""))
        if currency != "USD":
            amount = amount / exchange_rate(f"USD{currency}")
        capital += amount
    for item in c[NEGATIVES]:
        amount_str, currency = item[1].split(" ")
        amount = float(amount_str.replace(",", ""))
        if currency != "USD":
            amount = amount / exchange_rate(f"USD{currency}")
        debt += amount
    debt_to_assets = -debt / grand_total * 100
    response = make_response(
        f"Net Worth: {sum:10,.0f} USD"
        + f"\n\nTotal Capital: {capital:10,.0f} USD\nTotal Debt:    {debt:10,.0f} USD\nDebt to Assets Ratio:   {debt_to_assets:,.2f}%\n"
        + f"\n\nReturn on Assets: {(ret*100):,.2f}%\nEstimated Monthly: {sum*ret/12:7,.0f} USD\n\n"
        + f"Country Split: PY {sum_py/sum*100:3.2f}% USD\n               US {sum_us/sum*100:3.2f}% USD\n\nDetails:\n\n"
        + PRINTER.pformat(c),
        200,
    )
    response.mimetype = "text/plain"
    return response
