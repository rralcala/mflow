from datetime import datetime

import logging

from data.gdrive import list_files_in_folder
import data.internal


def income_at_month(date, items):
    totals = {"USD": 0.0, "PYG": 0.0}
    for k, v in items.items():
        for asset in v:
            # print(asset.identifier)
            income = asset.get_income(date)
            if income[0] == 0.0:
                continue
            logging.debug(f"++ UPCOMING {asset.identifier} {income[0]:,.2f}")
            if income[0] != 0.0:
                totals[k] += income[0]
    logging.debug(f"{date}: {totals["USD"]} {totals["PYG"]}")
    return totals["USD"], totals["PYG"]


def calculate_balance(items) -> float:
    totals = {"USD": 0.0, "PYG": 0.0}
    for k, v in items.items():
        for asset in v:
            income = asset.get_liquid_balance()
            if income[0] != 0.0:
                totals[k] += income[0]
    return totals["USD"] + totals["PYG"] / data.internal.exchange_rate("USDPYG")


def generate_timeline(end: datetime):
    files = list_files_in_folder()
    items = data.internal.fetch_assets(files)
    tls = []
    for k, v in items.items():
        for asset in v:
            tl = asset.get_timeline(end)
            tls.append((asset.country, tl))
    return tls


def cash_flow(today: datetime):
    logging.debug("Listing files in Google Drive folder:")
    files = list_files_in_folder()

    items = data.internal.fetch_assets(files)
    start = today.year * 12 + today.month - 1
    end = (today.year + 0) * 12 + today.month
    balance = calculate_balance(items)
    x = []
    balances = []
    t = []
    for v in range(start, end):
        year = v // 12
        month = v % 12 + 1
        today = datetime(year, month, 1)
        totalsd, totalsg = income_at_month(today, items)
        balance += totalsd + totalsg / data.internal.exchange_rate("USDPYG")
        balances.append(balance)
        x.append(f"{year}-{month:02d}")
        t.append((totalsd, totalsg))

    return x, balances, t
