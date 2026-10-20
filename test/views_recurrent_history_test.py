import unittest
from datetime import date
from test.rest_assets_test import api_app, run_view
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from data.base import Base
from lib.config import Config
from models.models import Recurrent, RecurrentTransaction
from routes import rest_reports
from views import recurrent_history as vrh


def recurrent(identifier, currency="PYG", flow_class="expense", user_id=1):
    return Recurrent(
        identifier=identifier,
        country="PY",
        amount="-100",
        currency=currency,
        recurrence="0 0 1 * *",
        start="2026-01-01",
        end="2030-01-01",
        flow_class=flow_class,
        rate="0",
        user_id=user_id,
    )


def transaction(parent_id, year_month, amount, user_id=1):
    return RecurrentTransaction(
        parent_id=parent_id,
        year_month=year_month,
        description="",
        amount=str(amount),
        transaction_date=f"{year_month}-15",
        paid_with="acc",
        user_id=user_id,
    )


class TestRecurrentHistory(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://")
        self.addCleanup(engine.dispose)
        Base.metadata.create_all(
            engine, tables=[Recurrent.__table__, RecurrentTransaction.__table__]
        )
        Session = sessionmaker(bind=engine)
        with Session() as session:
            session.add_all(
                [
                    recurrent("Food"),
                    recurrent("Rent", currency="USD", flow_class="income"),
                    recurrent("Power"),
                    recurrent("Theirs", user_id=2),
                    transaction("Food", "2026-01", -100),
                    transaction("Food", "2026-01", -50),
                    transaction("Food", "2026-03", -300),
                    transaction("Power", "2026-02", -60),
                    transaction("Rent", "2026-02", 1000),
                    transaction("Rent", "2026-03", 1000),
                    # Outside the range.
                    transaction("Food", "2025-12", -999),
                    transaction("Food", "2026-04", -999),
                    # A deleted recurrent, and another user's data.
                    transaction("Gone", "2026-02", -7),
                    transaction("Theirs", "2026-02", -5, user_id=2),
                ]
            )
            session.commit()
        db = patch.object(Config, "DB_SESSION", Session, create=True)
        db.start()
        self.addCleanup(db.stop)

    def history(self, **kwargs):
        return vrh.recurrent_history(1, "2026-01", "2026-03", **kwargs)

    def by_id(self, data):
        return {row["id"]: row for row in data["recurrents"]}

    def test_monthly_totals_per_recurrent(self):
        data = self.history()
        self.assertEqual(data["months"], ["2026-01", "2026-02", "2026-03"])
        rows = self.by_id(data)
        self.assertEqual(list(rows), ["Food", "Gone", "Power", "Rent"])
        self.assertEqual(rows["Food"]["months"], [-150.0, 0.0, -300.0])
        self.assertEqual(rows["Rent"]["months"], [0.0, 1000.0, 1000.0])
        keys = ("currency", "flowClass", "missing", "target")
        self.assertEqual(
            {key: rows["Food"][key] for key in keys},
            {
                "currency": "PYG",
                "flowClass": "expense",
                "missing": False,
                "target": -100.0,
            },
        )
        self.assertEqual(
            {key: rows["Gone"][key] for key in keys},
            {"currency": None, "flowClass": None, "missing": True, "target": None},
        )

    def test_stats_count_empty_months_as_zero(self):
        stats = self.by_id(self.history())["Food"]["stats"]
        self.assertEqual(
            stats,
            {
                "total": -450.0,
                "transactions": 3,
                "activeMonths": 2,
                "monthlyAverage": -150.0,
                "activeAverage": -225.0,
                "median": -150.0,
                "min": -300.0,
                "max": 0.0,
                "stdDev": stats["stdDev"],
            },
        )
        self.assertAlmostEqual(stats["stdDev"], 122.474, places=3)

    def test_totals_per_currency_skip_deleted_recurrents(self):
        totals = {row["currency"]: row for row in self.history()["totals"]}
        self.assertEqual(list(totals), ["PYG", "USD"])
        self.assertEqual(totals["PYG"]["months"], [-150.0, -60.0, -300.0])
        self.assertEqual(totals["PYG"]["stats"]["transactions"], 4)
        self.assertEqual(totals["USD"]["stats"]["total"], 2000.0)

    def test_flow_class_filter(self):
        data = self.history(flow_class="income")
        self.assertEqual(list(self.by_id(data)), ["Rent"])
        self.assertEqual([row["currency"] for row in data["totals"]], ["USD"])

    def test_empty_range(self):
        data = vrh.recurrent_history(1, "2020-01", "2020-02")
        self.assertEqual((data["recurrents"], data["totals"]), ([], []))

    def test_default_range(self):
        self.assertEqual(vrh.default_range(date(2026, 10, 12)), ("2025-11", "2026-10"))
        self.assertEqual(vrh.default_range(date(2026, 12, 1)), ("2026-01", "2026-12"))

    def test_invalid_ranges(self):
        for start, end in (
            ("2026-13", "2026-12"),
            ("2026-1", "2026-02"),
            ("2026-05", "2026-04"),
            ("2000-01", "2026-01"),
            (None, "2026-01"),
        ):
            with self.assertRaises(ValueError):
                vrh.month_range(start, end)

    def test_route(self):
        app = api_app()
        with patch.object(rest_reports, "current_user", SimpleNamespace(id="1")):
            with app.test_request_context(
                "/recurrent_history?startYearMonth=2026-02&endYearMonth=2026-03"
                "&flowClass=expense"
            ):
                response, status = run_view(rest_reports.recurrent_history)
                self.assertEqual(status, 200)
                self.assertEqual(response.headers["X-Total-Count"], "2")
                data = response.get_json()
                self.assertEqual(data["months"], ["2026-02", "2026-03"])
            with app.test_request_context("/recurrent_history?startYearMonth=bad"):
                response, status = run_view(rest_reports.recurrent_history)
                self.assertEqual(status, 400)
                self.assertIn("startYearMonth", response.get_json()["message"])


if __name__ == "__main__":
    unittest.main()
