from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from data.exchange_rates import ExchangeRates
from reports.cash_flow import generate_timeline


def _to_date(value: Optional[date | datetime]) -> date:
    if value is None:
        return date.today()
    if isinstance(value, datetime):
        return value.date()
    return value


def _bucket_date(value: date, granularity: str) -> date:
    if granularity == "yearly":
        return date(value.year, 1, 1)
    return date(value.year, value.month, 1)


def _next_bucket(value: date, granularity: str) -> date:
    if granularity == "yearly":
        return date(value.year + 1, 1, 1)

    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def _iter_buckets(start_date: date, end_date: date, granularity: str) -> List[date]:
    buckets: List[date] = []
    current = _bucket_date(start_date, granularity)
    while current <= end_date:
        buckets.append(current)
        current = _next_bucket(current, granularity)
    return buckets


def _safe_add_years(value: date, years: int) -> date:
    try:
        return value.replace(year=value.year + years)
    except ValueError:
        # Handle leap day by moving to Feb 28 on non-leap target years.
        return value.replace(month=2, day=28, year=value.year + years)


def _get_expiration_date(asset: Any) -> Optional[date]:
    for field in ("maturity_date", "due_date", "end_date"):
        raw = getattr(asset, field, None)
        if raw is None:
            continue
        if isinstance(raw, datetime):
            return raw.date()
        if isinstance(raw, date):
            return raw
    return None


def _flatten_assets(assets: Dict[str, List[Any]]) -> List[Any]:
    all_assets: List[Any] = []
    for bucket in assets.values():
        all_assets.extend(bucket)
    return all_assets


def _base_currency_value(amount: float, currency: str) -> float:
    if currency == "USD":
        return amount
    pair = f"USD{currency}"
    rate = ExchangeRates.exchange_rate(pair)
    if not rate:
        return 0.0
    return amount / rate


def _build_event_maps(
    assets: Dict[str, List[Any]],
    end_date: date,
    granularity: str,
    expiration_by_asset_id: Dict[str, Optional[date]],
    has_due_date_by_asset_id: Dict[str, bool],
) -> Tuple[Dict[Tuple[str, date], float], Dict[Tuple[str, date], float]]:
    yield_events: Dict[Tuple[str, date], float] = {}
    expiration_events: Dict[Tuple[str, date], float] = {}

    for _, asset_id, timeline in generate_timeline(
        assets, datetime.combine(end_date, datetime.min.time())
    ):
        expiration_date = expiration_by_asset_id.get(asset_id)
        expiration_bucket = (
            _bucket_date(expiration_date, granularity) if expiration_date else None
        )
        has_due_date = has_due_date_by_asset_id.get(asset_id, False)

        for timeline_date, (amount, _, is_capital) in timeline:
            bucket_date = _bucket_date(timeline_date, granularity)
            key = (asset_id, bucket_date)

            # Capital events at maturity and payable due-date events are treated as expiration.
            if is_capital and expiration_bucket == bucket_date:
                expiration_events[key] = expiration_events.get(key, 0.0) + amount
                continue

            if has_due_date and expiration_bucket == bucket_date:
                expiration_events[key] = expiration_events.get(key, 0.0) + amount
                continue

            if not is_capital:
                yield_events[key] = yield_events.get(key, 0.0) + amount

    return yield_events, expiration_events


def _resolve_end_date(
    all_assets: List[Any],
    start_date: date,
    end_date: Optional[date],
    fallback_years: int,
) -> date:
    if end_date is not None:
        return end_date

    latest_expiration: Optional[date] = None
    for asset in all_assets:
        expiration = _get_expiration_date(asset)
        if expiration is None or expiration < start_date:
            continue
        if latest_expiration is None or expiration > latest_expiration:
            latest_expiration = expiration

    if latest_expiration is not None:
        return latest_expiration

    return _safe_add_years(start_date, fallback_years)


def future_timeline(
    assets: Dict[str, List[Any]],
    mode: str = "aggregated",
    granularity: str = "monthly",
    start_date: Optional[date | datetime] = None,
    end_date: Optional[date | datetime] = None,
    include_non_expiring_value: bool = True,
    include_expirations: bool = True,
    include_yield: bool = True,
    fallback_years: int = 5,
) -> List[Dict[str, Any]]:
    """Build a chart-oriented projection view for value, yield and expiration timelines.

    This follows the repository's old-school view pattern where business projections live
    under views and are exposed by REST routes as database-like report projections.
    """
    if mode not in ("flat", "aggregated"):
        raise ValueError("mode must be one of: flat, aggregated")

    if granularity not in ("monthly", "yearly"):
        raise ValueError("granularity must be one of: monthly, yearly")

    start = _to_date(start_date)
    assets_list = _flatten_assets(assets)
    end = _resolve_end_date(
        assets_list, start, _to_date(end_date) if end_date else None, fallback_years
    )
    if end < start:
        return []

    buckets = _iter_buckets(start, end, granularity)

    expiration_by_asset_id: Dict[str, Optional[date]] = {
        asset.identifier: _get_expiration_date(asset) for asset in assets_list
    }
    has_due_date_by_asset_id: Dict[str, bool] = {
        asset.identifier: hasattr(asset, "due_date") for asset in assets_list
    }

    yield_events, expiration_events = _build_event_maps(
        assets,
        end,
        granularity,
        expiration_by_asset_id,
        has_due_date_by_asset_id,
    )

    flat_rows: List[Dict[str, Any]] = []
    for asset in assets_list:
        asset_id = asset.identifier
        asset_type = asset.__class__.__name__
        country = getattr(asset, "country", asset.get_location()[0])
        currency = asset.get_currency()
        current_value, _ = asset.get_current_value()
        expiration_date = expiration_by_asset_id[asset_id]
        expiration_bucket = (
            _bucket_date(expiration_date, granularity) if expiration_date else None
        )

        include_repeated_value = (
            include_non_expiring_value or expiration_date is not None
        )

        for bucket in buckets:
            if expiration_bucket is not None and bucket > expiration_bucket:
                value_amount = 0.0
            elif include_repeated_value:
                value_amount = current_value
            else:
                value_amount = 0.0

            yield_amount = (
                yield_events.get((asset_id, bucket), 0.0) if include_yield else 0.0
            )
            expiration_amount = (
                expiration_events.get((asset_id, bucket), 0.0)
                if include_expirations
                else 0.0
            )

            if value_amount == 0.0 and yield_amount == 0.0 and expiration_amount == 0.0:
                continue

            flat_rows.append(
                {
                    "id": f"{asset_id}-{bucket.isoformat()}",
                    "date": bucket.isoformat(),
                    "assetId": asset_id,
                    "country": country,
                    "type": asset_type,
                    "currency": currency,
                    "value": value_amount,
                    "yieldAmount": yield_amount,
                    "expirationAmount": expiration_amount,
                    "isExpiration": expiration_amount != 0.0,
                    "expirationDate": (
                        expiration_date.isoformat() if expiration_date else None
                    ),
                }
            )

    flat_rows.sort(key=lambda row: (row["date"], row["assetId"]))
    if mode == "flat":
        return flat_rows

    aggregated: Dict[str, Dict[str, Any]] = {}
    for row in flat_rows:
        date_key = row["date"]
        item = aggregated.setdefault(
            date_key,
            {
                "id": date_key,
                "date": date_key,
                "valueTotal": 0.0,
                "yieldTotal": 0.0,
                "expirationTotal": 0.0,
                "totalBaseCurrency": 0.0,
                "totalsByCurrencyCountry": {},
                "byType": {},
            },
        )

        point_total = row["value"] + row["yieldAmount"] + row["expirationAmount"]
        currency_country = f"{row['currency']}-{row['country']}"

        item["valueTotal"] += row["value"]
        item["yieldTotal"] += row["yieldAmount"]
        item["expirationTotal"] += row["expirationAmount"]
        item["totalBaseCurrency"] += _base_currency_value(point_total, row["currency"])

        cc_totals = item["totalsByCurrencyCountry"]
        cc_totals[currency_country] = cc_totals.get(currency_country, 0.0) + point_total

        by_type = item["byType"].setdefault(
            row["type"],
            {"value": 0.0, "yield": 0.0, "expiration": 0.0, "count": 0},
        )
        by_type["value"] += row["value"]
        by_type["yield"] += row["yieldAmount"]
        by_type["expiration"] += row["expirationAmount"]
        by_type["count"] += 1

    return [aggregated[d] for d in sorted(aggregated)]
