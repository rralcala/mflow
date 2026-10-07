"""Month-by-month simulation of every asset until UserConfig.LAST_UNTIL.

Each asset becomes a holding with a value. Dated events (recurrents, payables,
bond/CD coupons and maturities, instrument interest/dividends) move money into
the *target pool* named by the asset's ``target_asset_id`` (an Account id or an
Instrument identifier). Pools are what the user has to keep above zero.

Modeling rules:
  * Recurrent expenses/incomes and yearly (non one-off) payables grow with the
    inflation of their country. Loans and repayments are fixed contracts.
  * Housing properties grow with their country's inflation; vehicles don't.
    A property with a sell-by date is sold then at its simulated value into
    its target asset, and recurrents whose parent is that property stop.
  * Instruments pay ``rate`` on their cron schedule, computed on their current
    simulated value, into their target (themselves when unset, so cash-like
    sweeps compound). ``capital_rate`` appreciation is opt-in: compounding
    speculative rates for decades swamps everything else.
  * Transfers move value between assets in pairs: they change balances but
    are neither income nor expenses, and are never inflated.
  * Exchange rates are held constant at today's quotes.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import partial
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from asset_classes.account import Account
from asset_classes.bond import Bond
from asset_classes.instrument import Instrument
from asset_classes.payable import Payable
from asset_classes.property import Property
from asset_classes.recurrent import Recurrent
from data.constants import RecurrentTypes, is_transfer
from lib.util import cron_runs

DEFAULT_INFLATION_RATES: Dict[str, float] = {"US": 0.025, "UY": 0.025, "PY": 0.035}
FALLBACK_INFLATION_RATE = 0.025
VEHICLE_PREFIXES = ("auto", "car", "moto", "vehicle")
VEHICLE_MARKERS = ("VIN=", "Plates=")
INFLATION_INDEXED_FLOWS = (RecurrentTypes.Expense, RecurrentTypes.Income)
CATEGORIES = ("income", "expenses", "interest", "maturities", "sales", "transfers")
# Per-currency transfer totals below this (in USD) count as balanced.
TRANSFER_TOLERANCE_USD = 1.0


@dataclass
class _Holding:
    key: str
    name: str
    kind: str
    country: str
    currency: str
    value: float
    liquid: bool = False
    is_pool: bool = False
    is_fallback: bool = False
    growth: Optional[str] = None
    start_value: float = 0.0
    sold_on: Optional[str] = None


def _to_date(value: date | datetime | str) -> date:
    if isinstance(value, str):
        return datetime.strptime(value, "%Y-%m-%d").date()
    if isinstance(value, datetime):
        return value.date()
    return value


def _safe_replace_year(value: datetime, year: int) -> datetime:
    try:
        return value.replace(year=year)
    except ValueError:
        return value.replace(year=year, day=28)


def is_vehicle(asset: Property) -> bool:
    name = asset.get_identifier().lower()
    details = getattr(asset, "additional_data", "") or ""
    return name.startswith(VEHICLE_PREFIXES) or any(
        marker in details for marker in VEHICLE_MARKERS
    )


def market_fx_rates(assets: Dict[str, List[Any]]) -> Dict[str, float]:
    """Units of each held currency per USD, using today's quotes."""
    from data.exchange_rates import ExchangeRates

    rates = {"USD": 1.0}
    for asset in _flatten(assets):
        currency = asset.get_currency().upper()
        if currency not in rates:
            rate = ExchangeRates.exchange_rate("USD" + currency)
            if rate:
                rates[currency] = rate
    return rates


def _category(asset: Any, amount: float) -> str:
    if is_transfer(asset):
        return "transfers"
    return "income" if amount > 0 else "expenses"


def _flatten(assets: Dict[str, List[Any]]) -> Iterable[Any]:
    for bucket in assets.values():
        yield from bucket


class _Simulation:
    def __init__(
        self,
        start: date,
        end: date,
        inflation_rates: Dict[str, float],
        fx_rates: Dict[str, float],
        include_capital_growth: bool,
    ):
        self.start_dt = datetime.combine(start, datetime.min.time())
        self.end_dt = datetime.combine(end, datetime.max.time())
        self.inflation_rates = inflation_rates
        self.fx_rates = {k.upper(): v for k, v in fx_rates.items()}
        self.include_capital_growth = include_capital_growth

        self.months: List[date] = []
        current = date(start.year, start.month, 1)
        while current <= end:
            self.months.append(current)
            current = (current + timedelta(days=32)).replace(day=1)

        self.holdings: Dict[str, _Holding] = {}
        self.targets: Dict[str, str] = {}  # target_asset_id -> holding key
        self.events: List[List[Tuple[datetime, int, Callable[[], None]]]] = [
            [] for _ in self.months
        ]
        self.growth: List[Tuple[_Holding, float]] = []
        self.warnings: List[str] = []
        self.sale_dates: Dict[str, datetime] = {}  # property id -> sell-by
        self._pending: List[Tuple[Any, _Holding]] = []
        self._seq = 0
        self._flows: Dict[str, float] = {}
        self._transfer_nets: Dict[str, float] = {}  # currency -> native total
        self._month_min: Dict[str, float] = {}
        self._month = self.months[0]

    # -- setup -----------------------------------------------------------

    def inflation(self, country: str) -> float:
        return self.inflation_rates.get(country, FALLBACK_INFLATION_RATE)

    def inflation_factor(self, country: str, month_index: int) -> float:
        return (1 + self.inflation(country)) ** (month_index / 12)

    def month_index(self, when: datetime) -> Optional[int]:
        """Month bucket for an event; overdue events land in the first month."""
        if when > self.end_dt:
            return None
        index = (when.year - self.months[0].year) * 12 + when.month
        return max(0, index - self.months[0].month)

    def schedule(self, when: datetime, action: Callable[[], None]) -> None:
        index = self.month_index(when)
        if index is None:
            return
        self._seq += 1
        self.events[index].append((max(when, self.start_dt), self._seq, action))

    def add_holding(self, asset: Any, value: float, **kwargs) -> _Holding:
        kind = type(asset).__name__
        name = asset.get_identifier()
        key = name if name not in self.holdings else f"{kind}:{name}"
        holding = _Holding(
            key=key,
            name=name,
            kind=kind,
            country=getattr(asset, "country", "") or "",
            currency=asset.get_currency().upper(),
            value=value,
            start_value=value,
            **kwargs,
        )
        self.holdings[key] = holding
        return holding

    def add_assets(self, assets: Iterable[Any]) -> None:
        assets = list(assets)
        # Targets must exist before anything references them.
        for asset in assets:
            if isinstance(asset, Account):
                holding = self.add_holding(
                    asset, asset.get_current_value()[0], liquid=asset.is_liquid()
                )
                self.targets.setdefault(asset.get_identifier(), holding.key)
        for asset in assets:
            if isinstance(asset, Instrument):
                holding = self.add_holding(
                    asset, asset.get_current_value()[0], liquid=asset.is_liquid()
                )
                self.targets.setdefault(asset.get_identifier(), holding.key)
                self._pending.append((asset, holding))
        # Recurrents linked to a property stop when it's sold.
        for asset in assets:
            if isinstance(asset, Property) and asset.sell_by:
                self.sale_dates[asset.get_identifier()] = asset.sell_by
        for asset in assets:
            if isinstance(asset, (Account, Instrument)):
                continue
            if isinstance(asset, Bond):
                self.add_bond(asset)
            elif isinstance(asset, Recurrent):
                self.add_recurrent(asset)
            elif isinstance(asset, Payable):
                self.add_payable(asset)
            elif isinstance(asset, Property):
                self.add_property(asset)
            else:
                self.warnings.append(
                    f"{type(asset).__name__} {asset.get_identifier()} is not simulated."
                )
        for asset, holding in self._pending:
            self.add_instrument(asset, holding)

    def resolve_target(
        self, asset: Any, default: Optional[_Holding] = None
    ) -> _Holding:
        target_id = getattr(asset, "target_asset_id", "") or ""
        if target_id in self.targets:
            holding = self.holdings[self.targets[target_id]]
        elif not target_id and default is not None:
            holding = default
        else:
            if target_id:
                self.warnings.append(
                    f"{asset.get_identifier()} targets unknown asset '{target_id}'."
                )
            holding = self.fallback_pool(
                asset.get_currency().upper(), getattr(asset, "country", "")
            )
        holding.is_pool = True
        return holding

    def fallback_pool(self, currency: str, country: str) -> _Holding:
        key = f"Unassigned {currency} {country}".strip()
        if key not in self.holdings:
            self.holdings[key] = _Holding(
                key=key,
                name=key,
                kind="Unassigned",
                country=country,
                currency=currency,
                value=0.0,
                liquid=True,
                is_pool=True,
                is_fallback=True,
            )
        return self.holdings[key]

    def add_instrument(self, asset: Instrument, holding: _Holding) -> None:
        if self.include_capital_growth and asset.capital_rate:
            holding.growth = "capital"
            self.growth.append((holding, float(asset.capital_rate)))
        if not asset.rate:
            return
        first_year = cron_runs(
            asset.dividend,
            self.start_dt,
            self.start_dt + timedelta(days=365) - timedelta(seconds=1),
        )
        if not first_year:
            return
        rate_per_payout = float(asset.rate) / len(first_year)
        target = self.resolve_target(asset, default=holding)
        for run in cron_runs(asset.dividend, self.start_dt, self.end_dt):
            if run >= self.start_dt:
                self.schedule(
                    run, partial(self.pay_yield, holding, target, rate_per_payout)
                )

    def add_bond(self, asset: Bond) -> None:
        holding = self.add_holding(asset, asset.get_current_value()[0])
        target = self.resolve_target(asset)
        for payment in asset.payment_schedule:
            if not payment["paid"]:
                self.schedule(
                    payment["date"],
                    partial(
                        self.transfer,
                        None,
                        target,
                        payment["amount"],
                        holding.currency,
                        "interest",
                    ),
                )
        self.schedule(
            asset.maturity_date,
            partial(
                self.transfer,
                holding,
                target,
                asset.capital,
                holding.currency,
                "maturities",
            ),
        )

    def add_recurrent(self, asset: Recurrent) -> None:
        is_contract = asset.flow_class in (
            RecurrentTypes.Loan,
            RecurrentTypes.Repayment,
        )
        holding = self.add_holding(
            asset, asset.get_current_value()[0] if is_contract else 0.0
        )
        if not asset.amount:
            return
        target = self.resolve_target(asset)
        source = holding if is_contract else None
        indexed = asset.flow_class in INFLATION_INDEXED_FLOWS
        window_start = max(
            asset.start_date, datetime.combine(self.months[0], datetime.min.time())
        )
        window_end = min(asset.maturity_date, self.end_dt)
        sale = self.sale_dates.get(asset.parent_asset_id)
        if sale is not None:
            if asset.maturity_date.date() != sale.date():
                self.warnings.append(
                    f"{asset.get_identifier()} ends {asset.maturity_date.date()} but "
                    f"{asset.parent_asset_id} is sold {sale.date()}; the simulation "
                    "stops it at whichever comes first."
                )
            window_end = min(window_end, sale)
        for run in cron_runs(asset.recurrence, window_start, window_end):
            if run < window_start:
                continue
            index = self.month_index(run)
            amount = asset.amount
            if index == 0:
                # Discount what was already recorded as paid this month.
                for row in asset.fetch_transactions(run):
                    amount = round(amount - float(row.amount), 2)
                if asset.flow_class == RecurrentTypes.Expense and amount >= 0.0:
                    continue
            elif indexed:
                amount *= self.inflation_factor(holding.country, index)
            category = _category(asset, amount)
            self.schedule(
                run,
                partial(
                    self.transfer, source, target, amount, holding.currency, category
                ),
            )

    def add_payable(self, asset: Payable) -> None:
        holding = self.add_holding(asset, asset.get_current_value()[0])
        if not asset.balance:
            return
        target = self.resolve_target(asset)
        category = _category(asset, asset.balance)
        self.schedule(
            asset.due_date,
            partial(
                self.transfer,
                holding if asset.commited else None,
                target,
                asset.balance,
                holding.currency,
                category,
            ),
        )
        if asset.one_off:
            return
        # Regular payables are expected to come back every year, inflation
        # adjusted unless they are fixed contracts like loans.
        flow_class = (asset.flow_class or RecurrentTypes.Expense).lower()
        indexed = flow_class in INFLATION_INDEXED_FLOWS
        year = asset.due_date.year + 1
        while year <= self.end_dt.year:
            when = _safe_replace_year(asset.due_date, year)
            year += 1
            index = self.month_index(when)
            if index is None:
                break
            if when < self.start_dt:
                continue  # Overdue occurrence is already the original due date.
            amount = asset.amount
            if indexed:
                amount *= self.inflation_factor(holding.country, index)
            self.schedule(
                when,
                partial(
                    self.transfer, None, target, amount, holding.currency, category
                ),
            )

    def add_property(self, asset: Property) -> None:
        holding = self.add_holding(asset, asset.get_current_value()[0])
        if not is_vehicle(asset):
            holding.growth = "inflation"
            self.growth.append((holding, self.inflation(holding.country)))
        if asset.sell_by:
            target = self.resolve_target(asset)
            self.schedule(asset.sell_by, partial(self.sell, holding, target))

    # -- runtime ---------------------------------------------------------

    def convert(self, amount: float, source: str, target: str) -> float:
        if source == target:
            return amount
        return self.to_usd(amount, source) * self.rate(target)

    def rate(self, currency: str) -> float:
        if currency not in self.fx_rates:
            self.warnings.append(f"No exchange rate for {currency}, assuming 1:1 USD.")
            self.fx_rates[currency] = 1.0
        return self.fx_rates[currency]

    def to_usd(self, amount: float, currency: str) -> float:
        return amount / self.rate(currency)

    def transfer(
        self,
        source: Optional[_Holding],
        target: _Holding,
        amount: float,
        currency: str,
        category: str,
    ) -> None:
        if source is not None:
            source.value -= amount
        target.value += self.convert(amount, currency, target.currency)
        self._flows[category] += self.to_usd(amount, currency)
        if category == "transfers":
            self._transfer_nets[currency] = (
                self._transfer_nets.get(currency, 0.0) + amount
            )
        self._month_min[target.key] = min(
            self._month_min.get(target.key, target.value), target.value
        )

    def sell(self, holding: _Holding, target: _Holding) -> None:
        """Sell at the simulated value, so housing includes inflation to date."""
        holding.sold_on = self._month.isoformat()[:7]
        if holding.value:
            self.transfer(holding, target, holding.value, holding.currency, "sales")

    def transfers_balanced(self) -> bool:
        """A month's transfers balance when each currency nets to zero, or the
        leftovers move in opposite directions across currencies. Cross-currency
        pairs are entered at the user's own rate, so their amounts aren't compared.
        """
        leftovers = [
            net
            for currency, net in self._transfer_nets.items()
            if abs(self.to_usd(net, currency)) > TRANSFER_TOLERANCE_USD
        ]
        return not leftovers or (
            any(net > 0 for net in leftovers) and any(net < 0 for net in leftovers)
        )

    def pay_yield(self, source: _Holding, target: _Holding, rate: float) -> None:
        if source.value <= 0.0:
            return
        self.transfer(None, target, source.value * rate, source.currency, "interest")

    def run(self, desired_estate: float) -> Dict[str, Any]:
        pools = [h for h in self.holdings.values() if h.is_pool]
        pool_stats = {
            p.key: {
                "minBalance": p.value,
                "minDate": self.months[0].isoformat(),
                "firstNegativeDate": None,
                "monthsNegative": 0,
            }
            for p in pools
        }
        start_net_worth = self.net_worth()
        unbalanced_transfers: List[str] = []
        rows = []
        for index, month in enumerate(self.months):
            self._month = month
            self._flows = {category: 0.0 for category in CATEGORIES}
            self._transfer_nets = {}
            self._month_min = {p.key: p.value for p in pools}
            for _, _, action in sorted(self.events[index], key=lambda e: e[:2]):
                action()
            for holding, annual_rate in self.growth:
                if holding.value > 0.0:
                    holding.value *= (1 + annual_rate) ** (1 / 12)

            month_str = month.isoformat()
            if not self.transfers_balanced():
                unbalanced_transfers.append(month_str[:7])
            negative = []
            for pool in pools:
                low = min(self._month_min[pool.key], pool.value)
                stats = pool_stats[pool.key]
                if low < stats["minBalance"]:
                    stats["minBalance"] = low
                    stats["minDate"] = month_str
                if low < 0.0:
                    negative.append(pool.key)
                    stats["monthsNegative"] += 1
                    stats["firstNegativeDate"] = stats["firstNegativeDate"] or month_str

            rows.append(
                {
                    "id": month_str[:7],
                    "date": month_str,
                    **self._flows,
                    "netCashFlow": self._flows["income"]
                    + self._flows["expenses"]
                    + self._flows["interest"],
                    "cashTotal": sum(self.to_usd(p.value, p.currency) for p in pools),
                    "liquidTotal": sum(
                        self.to_usd(h.value, h.currency)
                        for h in self.holdings.values()
                        if h.liquid
                    ),
                    "netWorth": self.net_worth(),
                    "balances": {p.key: p.value for p in pools},
                    "minBalances": {
                        p.key: min(self._month_min[p.key], p.value) for p in pools
                    },
                    "negativePools": negative,
                }
            )

        if unbalanced_transfers:
            self.warnings.append(
                f"Transfers are missing their opposite side in "
                f"{len(unbalanced_transfers)} month(s), first in "
                f"{unbalanced_transfers[0]}: each transfer needs an opposite transfer "
                "in the same month (same amount within a currency, any amount across "
                "currencies)."
            )

        pool_rows = []
        for pool in pools:
            stats = pool_stats[pool.key]
            pool_rows.append(
                {
                    "id": pool.key,
                    "name": pool.name,
                    "type": pool.kind,
                    "country": pool.country,
                    "currency": pool.currency,
                    "liquid": pool.liquid,
                    "isFallback": pool.is_fallback,
                    "startBalance": pool.start_value,
                    "endBalance": pool.value,
                    **stats,
                    "requiredTopUp": max(0.0, -stats["minBalance"]),
                    "requiredTopUpUsd": max(
                        0.0, -self.to_usd(stats["minBalance"], pool.currency)
                    ),
                }
            )
        pool_rows.sort(key=lambda p: (p["firstNegativeDate"] is None, p["id"]))

        asset_rows = [
            {
                "id": h.key,
                "name": h.name,
                "type": h.kind,
                "country": h.country,
                "currency": h.currency,
                "growth": h.growth,
                "soldOn": h.sold_on,
                "isPool": h.is_pool,
                "startValue": h.start_value,
                "endValue": h.value,
                "startValueUsd": self.to_usd(h.start_value, h.currency),
                "endValueUsd": self.to_usd(h.value, h.currency),
            }
            for h in self.holdings.values()
            if h.start_value or h.value
        ]
        asset_rows.sort(key=lambda a: -abs(a["endValueUsd"]))

        negative_dates = [
            p["firstNegativeDate"] for p in pool_rows if p["firstNegativeDate"]
        ]
        low_cash = min(rows, key=lambda r: r["cashTotal"]) if rows else None
        end_net_worth = rows[-1]["netWorth"] if rows else start_net_worth
        return {
            "summary": {
                "startDate": self.start_dt.date().isoformat(),
                "endDate": self.end_dt.date().isoformat(),
                "months": len(rows),
                "startNetWorth": start_net_worth,
                "endNetWorth": end_net_worth,
                "desiredEstate": desired_estate,
                "estateGap": end_net_worth - desired_estate,
                "firstNegativeDate": min(negative_dates) if negative_dates else None,
                "negativePools": len(negative_dates),
                "requiredTopUpUsd": sum(p["requiredTopUpUsd"] for p in pool_rows),
                "minCashTotal": low_cash["cashTotal"] if low_cash else 0.0,
                "minCashTotalDate": low_cash["date"] if low_cash else None,
                "onTrack": not negative_dates and end_net_worth >= desired_estate,
            },
            "inflationRates": self.inflation_rates,
            "fxRates": self.fx_rates,
            "warnings": sorted(set(self.warnings)),
            "pools": pool_rows,
            "months": rows,
            "assets": asset_rows,
        }

    def net_worth(self) -> float:
        return sum(self.to_usd(h.value, h.currency) for h in self.holdings.values())


def future_timeline(
    assets: Dict[str, List[Any]],
    end_date: date | datetime | str,
    start_date: Optional[date | datetime] = None,
    inflation_rates: Optional[Dict[str, float]] = None,
    fx_rates: Optional[Dict[str, float]] = None,
    include_capital_growth: bool = False,
    desired_estate: float = 0.0,
) -> Dict[str, Any]:
    """Simulate every asset month by month from start_date until end_date."""
    start = _to_date(start_date or date.today())
    end = _to_date(end_date)
    if end < start:
        raise ValueError("endDate must not be before startDate")

    simulation = _Simulation(
        start,
        end,
        {**DEFAULT_INFLATION_RATES, **(inflation_rates or {})},
        fx_rates if fx_rates is not None else market_fx_rates(assets),
        include_capital_growth,
    )
    simulation.add_assets(_flatten(assets))
    return simulation.run(desired_estate)
