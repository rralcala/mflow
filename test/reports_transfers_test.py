import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from asset_classes.payable import Payable
from asset_classes.recurrent import Recurrent
from reports.pnl import calculate_monthly_pnl_data, monthly_transactions
from views.spending import spending_analysis

USER = SimpleNamespace(id="1")
USER_CONFIG = SimpleNamespace(SECONDARY_CURRENCY="PYG")


def recurrent(identifier, amount, flow_class):
    return Recurrent(
        identifier=identifier,
        parent_asset_id="",
        country="US",
        amount=amount,
        currency="USD",
        recurrence="0 0 5 * *",
        start=datetime(2020, 1, 1),
        end=datetime(2075, 1, 1),
        flow_class=flow_class,
    )


def assets():
    return {
        "USD": [
            recurrent("Rent", -1000.0, "expense"),
            recurrent("Salary", 3000.0, "income"),
            recurrent("Sweep-Out", -500.0, "transfer"),
            recurrent("Sweep-In", 500.0, "transfer"),
            Payable(
                "US",
                "USD",
                "Move",
                -200.0,
                -200.0,
                datetime.now(),
                False,
                False,
                "transfer",
            ),
        ],
        "PYG": [],
    }


class TestTransfersAreExcludedFromReports(unittest.TestCase):
    def test_pnl_totals_ignore_transfers(self):
        with patch("reports.pnl.current_user", USER), patch(
            "reports.pnl.UserStore.get_user_config", return_value=USER_CONFIG
        ):
            pnl = calculate_monthly_pnl_data(assets(), months=12)

        self.assertAlmostEqual(pnl["p_totals"]["USD"], 12 * 3000.0)
        self.assertAlmostEqual(pnl["n_totals"]["USD"], 12 * -1000.0)
        ids = {
            t["assetId"]
            for month in pnl["monthly_data"]
            for t in month["income"] + month["expenses"]
        }
        self.assertEqual(ids, {"Rent", "Salary"})

    def test_monthly_transactions_still_list_transfers(self):
        _, transactions = next(monthly_transactions(assets(), months=1))
        ids = {t["assetId"] for t in transactions}
        self.assertTrue({"Sweep-Out", "Sweep-In", "Move"} <= ids)

    def test_spending_analysis_ignores_transfers(self):
        with patch("views.spending.current_user", USER), patch(
            "views.spending.UserStore.get_user_config", return_value=USER_CONFIG
        ), patch("views.spending.ExchangeRates.exchange_rate", return_value=7000.0):
            result = spending_analysis(assets())

        self.assertNotIn("transfer", result["total_budget"])
        self.assertAlmostEqual(result["total_budget"]["expense"], -1000.0)
        self.assertAlmostEqual(result["total_budget"]["income"], 3000.0)


if __name__ == "__main__":
    unittest.main()
