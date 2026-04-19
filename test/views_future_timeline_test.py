import unittest
from datetime import date, datetime

from views.future_timeline import future_timeline


class StubAsset:
    def __init__(
        self,
        identifier,
        country,
        currency,
        current_value,
        timeline,
        maturity_date=None,
        due_date=None,
    ):
        self.identifier = identifier
        self.country = country
        self._currency = currency
        self._current_value = current_value
        self._timeline = timeline
        if maturity_date is not None:
            self.maturity_date = maturity_date
        if due_date is not None:
            self.due_date = due_date

    def get_timeline(self, end):
        end_date = end.date()
        return [entry for entry in self._timeline if entry[0] <= end_date]

    def get_current_value(self):
        return self._current_value, self._currency

    def get_currency(self):
        return self._currency

    def get_location(self):
        return self.country, "stub"


class TestFutureTimelineView(unittest.TestCase):
    def test_flat_monthly_includes_value_yield_and_expiration(self):
        bond = StubAsset(
            identifier="bond-1",
            country="US",
            currency="USD",
            current_value=100.0,
            timeline=[
                (date(2030, 2, 1), (10.0, "USD", False)),
                (date(2030, 3, 15), (100.0, "USD", True)),
            ],
            maturity_date=datetime(2030, 3, 15),
        )
        account = StubAsset(
            identifier="cash-1",
            country="US",
            currency="USD",
            current_value=50.0,
            timeline=[],
        )

        rows = future_timeline(
            {"USD": [bond, account]},
            mode="flat",
            granularity="monthly",
            start_date=date(2030, 1, 1),
            end_date=date(2030, 3, 31),
            include_non_expiring_value=True,
        )

        cash_rows = [r for r in rows if r["assetId"] == "cash-1"]
        self.assertEqual(len(cash_rows), 3)
        self.assertTrue(all(r["value"] == 50.0 for r in cash_rows))

        feb_bond = next(
            r for r in rows if r["assetId"] == "bond-1" and r["date"] == "2030-02-01"
        )
        mar_bond = next(
            r for r in rows if r["assetId"] == "bond-1" and r["date"] == "2030-03-01"
        )
        self.assertEqual(feb_bond["yieldAmount"], 10.0)
        self.assertEqual(mar_bond["expirationAmount"], 100.0)
        self.assertTrue(mar_bond["isExpiration"])

    def test_aggregated_yearly_marks_payable_due_as_expiration(self):
        payable = StubAsset(
            identifier="pay-1",
            country="US",
            currency="USD",
            current_value=0.0,
            timeline=[(date(2031, 6, 10), (-20.0, "USD", False))],
            due_date=datetime(2031, 6, 10),
        )

        rows = future_timeline(
            {"USD": [payable]},
            mode="aggregated",
            granularity="yearly",
            start_date=date(2031, 1, 1),
            end_date=date(2031, 12, 31),
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["date"], "2031-01-01")
        self.assertEqual(rows[0]["expirationTotal"], -20.0)
        self.assertEqual(rows[0]["yieldTotal"], 0.0)

    def test_default_end_date_uses_latest_expiration(self):
        expiring = StubAsset(
            identifier="bond-2",
            country="US",
            currency="USD",
            current_value=10.0,
            timeline=[(date(2032, 1, 10), (10.0, "USD", True))],
            maturity_date=datetime(2032, 1, 10),
        )

        rows = future_timeline(
            {"USD": [expiring]},
            mode="flat",
            granularity="yearly",
            start_date=date(2030, 1, 1),
        )

        dates = [row["date"] for row in rows]
        self.assertIn("2032-01-01", dates)


if __name__ == "__main__":
    unittest.main()
