import io
from datetime import datetime

from dateutil.relativedelta import relativedelta

from data.internal import exchange_rate


def monthly_pnl(main_assets, include_income: bool, include_expenses: bool) -> str:
    start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    output = io.StringIO()

    grand_totals = {"USD": 0.0, "PYG": 0.0}
    for _ in range(12):
        nsums = {}
        psums = {}
        expenses_str = io.StringIO()
        income_str = io.StringIO()
        for currency, assets in main_assets.items():
            nsums[currency] = 0.0
            psums[currency] = 0.0
            for asset in assets:
                income = asset.get_income(start, include_capital=False)
                if income[0] < 0.0:
                    expenses_str.write(
                        asset.identifier + ": " + f"{income[0]:,.2f} {income[1]}\n"
                    )
                    nsums[currency] += income[0]
                elif income[0] > 0.0:
                    psums[currency] += income[0]
                    income_str.write(
                        asset.identifier + ": " + f"{income[0]:,.2f} {income[1]}\n"
                    )
        output.write(f"\n== {start.strftime("%Y %B")} ==\n")
        output.write("\n")
        if include_income:
            income_str.seek(0)
            output.write(income_str.read() + "\n")
            income_str.close()
        if include_expenses:
            expenses_str.seek(0)
            output.write(expenses_str.read() + "\n")
            expenses_str.close()

        output.write(
            f"Income:   {psums['PYG']:>12,.0f} Income:   {psums['USD']:>12,.2f}\n"
        )
        output.write(
            f"Expenses: {nsums['PYG']:>12,.0f} Expenses: {nsums['USD']:>12,.2f}\n"
        )
        output.write(
            f"Total:    {psums['PYG'] + nsums['PYG']:>12,.0f} Total:    {psums['USD'] + nsums['USD']:>12,.2f}\n"
        )
        grand_totals["PYG"] += psums["PYG"] + nsums["PYG"]
        grand_totals["USD"] += psums["USD"] + nsums["USD"]
        start = start + relativedelta(months=1)
    output.write(
        f"\nGrand Totals: PYG {grand_totals['PYG']:12,.0f}\n              USD    {grand_totals['USD']:12,.2f}\n\n"
    )
    output.write(
        f"Net:          PYG {(grand_totals['PYG'] + grand_totals['USD']*exchange_rate("USDPYG")):12,.0f}\n"
    )
    ret = output.getvalue()
    output.close()
    return ret
