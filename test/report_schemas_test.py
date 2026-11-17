"""Report output schemas against real view output.

Output schemas drop keys they don't declare, so each report's payload must
dump to itself: a key a view adds and its schema lacks would vanish from the
API.
"""

import json
import unittest
from datetime import date, datetime
from test import views_recurrent_history_test as history_test
from test.reports_transfers_test import USER, USER_CONFIG
from test.reports_transfers_test import assets as pnl_assets
from test.views_future_timeline_test import account, instrument, recurrent, run
from test.views_list_income_test import make_income, make_property
from unittest.mock import patch

from asset_classes.payable import Payable
from asset_classes.recurrent import Recurrent
from routes import schemas as s
from views import investment_performance as vip
from views import list_assets as vla
from views import monthly_pnl as vmpnl
from views import spending as vs


def as_json(data):
    """What the client receives: tuples become lists."""
    return json.loads(json.dumps(data))


class TestReportSchemas(unittest.TestCase):
    def assert_round_trip(self, schema, data):
        self.assertEqual(as_json(schema.dump(data)), as_json(data))

    def assert_declares(self, schema, row):
        """Every key in `row` is a field of `schema` (by its API name)."""
        names = {field.data_key or name for name, field in schema.fields.items()}
        self.assertEqual(set(row) - names, set())

    @patch.object(Recurrent, "fetch_transactions", return_value=[])
    @patch.object(Recurrent, "get_current_value", return_value=(0.0, "USD"))
    def test_future_timeline(self, *_):
        sweep = instrument(target="Sweep_A_USD", rate=0.12)
        sweep.is_target_pool = True
        old = account("OldBank", 500.0)
        old.transfer_by = datetime(2030, 3, 1)
        old.target_asset_id = "Sweep_A_USD"
        fund = instrument("Broker", "BND", 1000.0, liquid=False, target="Checking")
        fund.sell_by = datetime(2030, 6, 1)
        data = run(
            [account(), sweep, old, fund, recurrent(target="Checking")],
            end=date(2030, 12, 31),
            desired_estate=1_000_000.0,
        )
        self.assertTrue(data["warnings"] or data["pools"])
        self.assertTrue(any(a["soldOn"] for a in data["assets"]))
        self.assert_declares(s.FutureTimelineOut(), data)
        self.assert_declares(s.TimelineSummaryOut(), data["summary"])
        self.assert_declares(s.TimelinePoolOut(), data["pools"][0])
        self.assert_declares(s.TimelineMonthOut(), data["months"][0])
        self.assert_declares(s.TimelineAssetOut(), data["assets"][0])
        self.assert_round_trip(s.FutureTimelineOut(), data)

    def test_monthly_pnl(self):
        with patch("reports.pnl.current_user", USER), patch(
            "reports.pnl.UserStore.get_user_config", return_value=USER_CONFIG
        ), patch("views.monthly_pnl.current_user", USER), patch(
            "views.monthly_pnl.UserStore.get_user_config", return_value=USER_CONFIG
        ):
            year_months, summary = vmpnl.monthly_pnl(pnl_assets())
        data = {"year_months": year_months, "summary": summary}
        self.assert_declares(s.MonthlyPnlSummaryOut(), summary)
        self.assert_round_trip(s.MonthlyPnlOut(), data)

    def test_spending_analysis(self):
        with patch("views.spending.current_user", USER), patch(
            "views.spending.UserStore.get_user_config", return_value=USER_CONFIG
        ), patch("views.spending.ExchangeRates.exchange_rate", return_value=7000.0):
            data = vs.spending_analysis(pnl_assets())
        self.assertTrue(data["total_budget"])
        self.assert_declares(s.SpendingAnalysisOut(), data)
        self.assert_round_trip(s.SpendingAnalysisOut(), data)

    def portfolio(self):
        return {
            "USD": [
                make_property("Seattle-1", 800.0),
                make_income("AIRBNB-SEATTLE-1", "Seattle-1", 120.0),
                account("Checking", 200.0),
            ]
        }

    def test_income_per_location(self):
        with patch("views.list_assets.ExchangeRates.exchange_rate", return_value=10.0):
            data = vla.list_income(self.portfolio(), "PYG")
        self.assertTrue(data["tot_per_location"])
        self.assert_declares(s.IncomePerLocationOut(), data)
        self.assert_round_trip(s.IncomePerLocationOut(), data)

    def test_net_worth_summary(self):
        # list_assets also records this month's net worth; keep it off the DB.
        with patch(
            "views.list_assets.ExchangeRates.exchange_rate", return_value=10.0
        ), patch("views.list_assets.current_user", USER), patch(
            "views.list_assets.Config.DB_SESSION", create=True
        ):
            data = vla.list_assets(self.portfolio())
        self.assertTrue(data["tot_per_location"])
        self.assert_declares(s.NetWorthSummaryOut(), data)
        self.assert_round_trip(s.NetWorthSummaryOut(), data)

    def test_investment_performance(self):
        with patch(
            "reports.list_assets.ExchangeRates.exchange_rate", return_value=10.0
        ):
            data = vip.investment_performance(self.portfolio())
        self.assertTrue(any(band["assets"] for band in data))
        for band in data:
            self.assert_declares(s.PerformanceBandOut(), band)
        self.assert_round_trip(s.PerformanceBandOut(many=True), data)

    def test_investment_performance_skips_payables(self):
        portfolio = self.portfolio()
        portfolio["USD"].append(
            Payable("US", "USD", "TAXES", 500.0, 500.0, datetime(2030, 1, 1), True, "")
        )
        with patch(
            "reports.list_assets.ExchangeRates.exchange_rate", return_value=10.0
        ):
            data = vip.investment_performance(portfolio)
        names = [a[0] for band in data for a in band["assets"]]
        self.assertTrue(names)
        self.assertNotIn("TAXES", names)


class TestRecurrentHistorySchema(unittest.TestCase):
    setUp = history_test.TestRecurrentHistory.setUp
    history = history_test.TestRecurrentHistory.history

    def test_schema_round_trip(self):
        data = self.history()
        self.assertTrue(data["recurrents"] and data["totals"])
        schema = s.RecurrentHistoryOut()
        self.assertEqual(as_json(schema.dump(data)), as_json(data))
        row_fields = set(s.RecurrentHistoryRowOut().fields)
        for row in data["recurrents"]:
            self.assertEqual(set(row) - row_fields, set())


if __name__ == "__main__":
    unittest.main()
