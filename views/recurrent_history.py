"""Historical totals per recurrent, from the transactions actually recorded.

Unlike the other cash-flow reports this looks only at the past: it reads
`recurrent_transaction` rows and never simulates budgeted amounts.
"""

import statistics
from datetime import date
from typing import Dict, List, Optional

from lib.config import Config
from models.models import Recurrent, RecurrentTransaction

# Bounds the size of the response (ten years).
MAX_MONTHS = 120


def parse_year_month(value: str) -> date:
    try:
        parsed = date.fromisoformat(f"{value}-01")
    except (TypeError, ValueError):
        parsed = None
    if parsed is None or not isinstance(value, str) or len(value) != 7:
        raise ValueError(f"Invalid year month '{value}', expected YYYY-MM")
    return parsed


def month_range(start: str, end: str) -> List[str]:
    """Every YYYY-MM from `start` to `end`, inclusive."""
    first, last = parse_year_month(start), parse_year_month(end)
    if first > last:
        raise ValueError("startYearMonth is after endYearMonth")
    months = []
    year, month = first.year, first.month
    while (year, month) <= (last.year, last.month):
        months.append(f"{year:04d}-{month:02d}")
        if len(months) > MAX_MONTHS:
            raise ValueError(f"Range is longer than {MAX_MONTHS} months")
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return months


def default_range(today: date) -> tuple:
    """The twelve months ending with the current one."""
    months = today.year * 12 + today.month - 1 - 11
    return f"{months // 12:04d}-{months % 12 + 1:02d}", today.strftime("%Y-%m")


def series_stats(values: List[float], transactions: int) -> Dict:
    """Statistics over monthly totals; months without transactions count as 0."""
    active = [value for value in values if value != 0]
    total = sum(values)
    return {
        "total": total,
        "transactions": transactions,
        "activeMonths": len(active),
        "monthlyAverage": total / len(values),
        "activeAverage": total / len(active) if active else None,
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
        "stdDev": statistics.pstdev(values),
    }


def recurrent_history(
    user_id: int,
    start: str,
    end: str,
    flow_class: Optional[str] = None,
) -> Dict:
    months = month_range(start, end)
    index = {month: i for i, month in enumerate(months)}
    with Config.DB_SESSION() as session:
        recurrents = {
            row.identifier: row
            for row in session.query(Recurrent).filter_by(user_id=user_id).all()
        }
        transactions = (
            session.query(
                RecurrentTransaction.parent_id,
                RecurrentTransaction.year_month,
                RecurrentTransaction.amount,
            )
            .filter(
                RecurrentTransaction.user_id == user_id,
                RecurrentTransaction.year_month >= months[0],
                RecurrentTransaction.year_month <= months[-1],
            )
            .all()
        )

    series: Dict[str, Dict] = {}
    for parent_id, year_month, amount in transactions:
        if year_month not in index:
            continue
        recurrent = recurrents.get(parent_id)
        # Transactions whose recurrent was deleted are kept, without a currency.
        if flow_class and (recurrent is None or recurrent.flow_class != flow_class):
            continue
        entry = series.setdefault(
            parent_id,
            {
                "id": parent_id,
                "currency": recurrent.currency if recurrent else None,
                "flowClass": recurrent.flow_class if recurrent else None,
                "missing": recurrent is None,
                # The recurrent's stored amount; months are compared against it.
                "target": float(recurrent.amount) if recurrent else None,
                "values": [0.0] * len(months),
                "transactions": 0,
            },
        )
        entry["values"][index[year_month]] += float(amount)
        entry["transactions"] += 1

    rows = []
    totals: Dict[str, Dict] = {}
    for entry in sorted(series.values(), key=lambda x: x["id"]):
        values = [round(value, 2) for value in entry.pop("values")]
        count = entry.pop("transactions")
        rows.append({**entry, "months": values, "stats": series_stats(values, count)})
        if entry["currency"]:
            total = totals.setdefault(
                entry["currency"],
                {"values": [0.0] * len(months), "transactions": 0},
            )
            total["values"] = [a + b for a, b in zip(total["values"], values)]
            total["transactions"] += count

    return {
        "months": months,
        "recurrents": rows,
        "totals": [
            {
                "currency": currency,
                "months": [round(value, 2) for value in total["values"]],
                "stats": series_stats(total["values"], total["transactions"]),
            }
            for currency, total in sorted(totals.items())
        ],
    }
