import unittest
import unittest.mock
from datetime import date, datetime, timedelta

from asset_classes.account import Account
from asset_classes.payable import Payable
from asset_classes.recurrent import Recurrent


class TestAccountTimeline(unittest.TestCase):
    def setUp(self):
        self.fixed_today = date(2024, 6, 1)
        self.patcher = unittest.mock.patch("asset_classes.account.datetime")
        self.mock_datetime = self.patcher.start()
        self.mock_datetime.today.return_value = datetime(2024, 6, 1)
        self.mock_datetime.side_effect = lambda *args, **kwargs: datetime(
            *args, **kwargs
        )

    def tearDown(self):
        self.patcher.stop()

    def test_savings_account_positive_balance(self):
        acc = Account("US", "Bank", "123", "USD", 100.0, 1.0, "Savings")
        timeline = acc.get_timeline(datetime(2024, 6, 1))
        self.assertEqual(len(timeline), 1)
        self.assertEqual(timeline[0][0], self.fixed_today)
        self.assertEqual(timeline[0][1], (100.0, "USD", True))

    def test_checking_account_positive_balance(self):
        acc = Account("US", "Bank", "456", "USD", 200.0, 1.0, "Checking")
        timeline = acc.get_timeline(datetime(2024, 6, 1))
        self.assertEqual(len(timeline), 1)
        self.assertEqual(timeline[0][0], self.fixed_today)
        self.assertEqual(timeline[0][1], (200.0, "USD", True))

    def test_investment_account_non_liquid(self):
        acc = Account(
            "US", "Bank", "789", "USD", 300.0, 1.0, "Investment", liquid=False
        )
        timeline = acc.get_timeline(datetime(2024, 6, 1))
        self.assertEqual(timeline, [])

    def test_liquid_balance_applies_factor(self):
        acc = Account("US", "Bank", "F", "USD", 1000.0, 0.7, "Savings")
        self.assertEqual(acc.get_liquid_balance(), acc.get_current_value())
        timeline = acc.get_timeline(datetime(2024, 6, 1))
        self.assertAlmostEqual(timeline[0][1][0], 700.0)

    def test_non_liquid_balance_keeps_currency(self):
        acc = Account("PY", "Bank", "P", "PYG", 1000.0, 1.0, "Savings", liquid=False)
        self.assertEqual(acc.get_liquid_balance(), (0.0, "PYG"))

    def test_savings_account_zero_balance(self):
        acc = Account("US", "Bank", "000", "USD", 0.0, 1.0, "Savings")
        timeline = acc.get_timeline(datetime(2024, 6, 1))
        self.assertEqual(timeline, [])


class TestRecurrentTimeline(unittest.TestCase):
    def test_timeline_stops_at_maturity(self):
        maturity = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        maturity += timedelta(days=62)
        recurrent = Recurrent(
            identifier="School",
            parent_asset_id="",
            country="US",
            amount=-100.0,
            currency="USD",
            recurrence="0 0 5 * *",
            start=datetime(2020, 1, 1),
            end=maturity,
            flow_class="expense",
        )
        with unittest.mock.patch.object(
            Recurrent, "fetch_transactions", return_value=[]
        ):
            timeline = recurrent.get_timeline(maturity + timedelta(days=365))

        self.assertTrue(timeline)
        self.assertTrue(all(day <= maturity.date() for day, _ in timeline))


class TestPayableUsesBalance(unittest.TestCase):
    def setUp(self):
        self.payable = Payable(
            "US",
            "USD",
            "Tuition",
            -9000.0,
            -1000.0,
            datetime(2030, 7, 7),
            True,
            True,
            "expense",
        )

    def test_budget_is_balance_in_due_month(self):
        self.assertEqual(
            self.payable.get_budgeted_income(datetime(2030, 7, 1)), (-1000.0, "USD")
        )
        self.assertEqual(
            self.payable.get_budgeted_income(datetime(2030, 8, 1)), (0.0, "USD")
        )

    def test_actual_income_ignores_amount(self):
        self.assertEqual(
            self.payable.get_actual_income(datetime(2030, 7, 1)), (0.0, "USD")
        )


class TestRecurrentTransactionsPerUser(unittest.TestCase):
    def test_transactions_are_filtered_by_user(self):
        recurrent = Recurrent(
            identifier="Rent",
            parent_asset_id="",
            country="US",
            amount=-100.0,
            currency="USD",
            recurrence="0 0 5 * *",
            start=datetime(2026, 1, 1),
            end=datetime(2027, 1, 1),
            flow_class="loan",
            user_id=1,
        )
        session = unittest.mock.MagicMock()
        session.__enter__.return_value = session
        query = session.query.return_value
        query.filter_by.return_value.all.return_value = []
        with unittest.mock.patch(
            "asset_classes.recurrent.Config.DB_SESSION",
            return_value=session,
            create=True,
        ):
            recurrent.get_current_value()
            recurrent.fetch_transactions(datetime(2026, 10, 1))

        for call in query.filter_by.call_args_list:
            self.assertEqual(call.kwargs["user_id"], 1)
        self.assertEqual(query.filter_by.call_count, 2)


if __name__ == "__main__":
    unittest.main()
