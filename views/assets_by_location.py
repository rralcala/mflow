from typing import Any, Dict, List

from data.exchange_rates import ExchangeRates
from reports.list_assets import list_assets_by_location


def generate_summary_table(prop_sum, non_prop_sum) -> Dict[str, Dict[str, Any]]:
    countries = {}
    for country in prop_sum.keys():
        total = prop_sum[country] + non_prop_sum[country]
        summary_table = {
            "prop": prop_sum[country],
            "non_prop": non_prop_sum[country],
            "total": total,
            "prop_pct": prop_sum[country] / total * 100 if total > 0 else 0.0,
            "non_prop_pct": non_prop_sum[country] / total * 100 if total > 0 else 0.0,
        }
        countries[country] = summary_table
    return countries


def assets_by_location_data(assets) -> List[List[Any]]:
    _, _, prop_sum, non_prop_sum = generate_asset_split(assets)
    data = generate_summary_table(prop_sum, non_prop_sum)
    results = [["Location: Asset type", "Value"]]
    for country, summary in data.items():
        prop = [country + ": Property", summary["prop"]]
        non_prop = [country + ": Non-Property", summary["non_prop"]]
        results.append(prop)
        results.append(non_prop)
    return results


def generate_asset_split(assets):
    summary = list_assets_by_location(assets, print_pos=True, print_neg=False)
    loc_summary = []
    tot = 0.0
    prop_sum = {}
    non_prop_sum = {}
    for country, items in summary.items():
        prop_sum.setdefault(country, 0.0)
        non_prop_sum.setdefault(country, 0.0)
        for location, assets in items.items():
            location_sum = 0.0
            ct = 0
            for asset in assets:
                if asset[2] != "USD":
                    value = asset[1] / ExchangeRates.exchange_rate("USD" + asset[2])

                else:
                    value = asset[1]
                location_sum += value

                if asset[3] == "Property":
                    prop_sum[country] += value
                else:
                    non_prop_sum[country] += value
                ct += 1
            loc_summary.append([country, location, location_sum, ct])
            tot += location_sum

    loc_summary = sorted(loc_summary, key=lambda x: x[2], reverse=True)
    return loc_summary, tot, prop_sum, non_prop_sum
