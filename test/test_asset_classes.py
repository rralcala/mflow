import unittest
from datetime import date, datetime

from asset_classes.account import Account


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
        self.assertEqual(timeline[0][1], (100.0, "USD"))

    def test_checking_account_positive_balance(self):
        acc = Account("US", "Bank", "456", "USD", 200.0, 1.0, "Checking")
        timeline = acc.get_timeline(datetime(2024, 6, 1))
        self.assertEqual(len(timeline), 1)
        self.assertEqual(timeline[0][0], self.fixed_today)
        self.assertEqual(timeline[0][1], (200.0, "USD"))

    def test_investment_account_non_liquid(self):
        acc = Account("US", "Bank", "789", "USD", 300.0, 1.0, "Investment")
        timeline = acc.get_timeline(datetime(2024, 6, 1))
        self.assertEqual(timeline, [])

    def test_savings_account_zero_balance(self):
        acc = Account("US", "Bank", "000", "USD", 0.0, 1.0, "Savings")
        timeline = acc.get_timeline(datetime(2024, 6, 1))
        self.assertEqual(timeline, [])


if __name__ == "__main__":
    unittest.main()
