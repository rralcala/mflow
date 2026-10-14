import unittest
from test.rest_assets_test import QueryStub, SessionStub
from types import SimpleNamespace
from unittest.mock import patch

from apiflask import HTTPError
from flask import Flask

from lib.config import Config
from lib.util import normalize_flow_class, require_number
from models.models import Account, Recurrent, RecurrentTransaction
from routes.assets import rest_assets, rest_certificates, rest_recurrents


class TestRequireNumber(unittest.TestCase):
    def test_numbers_are_stored_as_float_strings(self):
        for value, stored in (
            (100, "100.0"),
            (-2.5, "-2.5"),
            ("0.05", "0.05"),
            (" 12 ", "12.0"),
            ("1e3", "1000.0"),
        ):
            with self.subTest(value=value):
                self.assertEqual(require_number(value, "amount"), stored)

    def test_anything_else_is_a_400(self):
        for value in (None, "", "abc", "1,000", True, "nan", "inf", [1], {}):
            with self.subTest(value=value), self.assertRaises(HTTPError) as ctx:
                require_number(value, "amount")
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertIn("amount", ctx.exception.message)


class TestNormalizeFlowClass(unittest.TestCase):
    def test_known_classes_are_lower_cased(self):
        self.assertEqual(normalize_flow_class("Expense"), "expense")
        self.assertEqual(normalize_flow_class(" income "), "income")
        self.assertEqual(normalize_flow_class("transfer"), "transfer")

    def test_missing_or_unknown_is_a_400(self):
        for value in (None, "", "rent", 5):
            with self.subTest(value=value), self.assertRaises(HTTPError) as ctx:
                normalize_flow_class(value)
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertIn("flowClass", ctx.exception.message)


# (url, view, module, valid body, numeric fields) for every POST that writes
# numeric columns.
POSTS = [
    (
        "/accounts",
        rest_assets.accounts,
        "rest_assets",
        {"id": "a", "country": "US", "currency": "usd", "balance": 100, "factor": 1},
        ["balance", "factor"],
    ),
    (
        "/instruments",
        rest_assets.instruments,
        "rest_assets",
        {
            "country": "US",
            "currency": "usd",
            "acquisition_date": "2026-01-01",
            "location": "Citi",
            "symbol": "VOO",
            "factor": 1,
            "qty": 1,
            "dividend": "N",
            "dividend_rate": 0,
            "acquisition_price": 1,
            "capital_rate": 0,
        },
        ["factor", "qty", "dividend_rate", "acquisition_price", "capital_rate"],
    ),
    (
        "/payables",
        rest_assets.payables,
        "rest_assets",
        {
            "country": "US",
            "currency": "usd",
            "dueDate": "2026-12-01",
            "amount": 10,
            "balance": 10,
            "flowClass": "expense",
        },
        ["amount", "balance"],
    ),
    (
        "/properties",
        rest_assets.properties,
        "rest_assets",
        {
            "country": "US",
            "currency": "usd",
            "purchasePrice": 1,
            "purchaseDate": "2020-01-01",
            "currentPrice": 1,
            "rentPrice": 0,
            "depreciation": 0,
            "rentCurrency": "usd",
        },
        ["purchasePrice", "currentPrice", "rentPrice", "depreciation"],
    ),
    (
        "/recurrents",
        rest_recurrents.recurrents_all,
        "rest_recurrents",
        {
            "id": "r",
            "country": "US",
            "currency": "usd",
            "start": "2026-01-01",
            "end": "2027-01-01",
            "recurrence": "0 0 5 * *",
            "amount": -100,
            "rate": 0,
            "flowClass": "expense",
        },
        ["amount", "rate"],
    ),
    (
        "/recurrentTransactions",
        rest_recurrents.recurrent_transactions,
        "rest_recurrents",
        {"recurrentId": "r", "yearMonth": "2026-01", "amount": -5},
        ["amount"],
    ),
    (
        "/bonds",
        rest_certificates.bonds_all,
        "rest_certificates",
        {
            "currency": "usd",
            "country": "US",
            "maturityDate": "2030-01-01",
            "capital": 1000,
            "rate": 0.05,
        },
        ["capital", "rate"],
    ),
    (
        "/depositCertificates",
        rest_certificates.deposit_certificates_all,
        "rest_certificates",
        {
            "currency": "usd",
            "country": "US",
            "maturityDate": "2030-01-01",
            "capital": 1000,
            "rate": 0.05,
        },
        ["capital", "rate"],
    ),
    (
        "/bondSchedules",
        rest_certificates.bond_schedules_all,
        "rest_certificates",
        {"bondId": 1, "transactionDate": "2026-01-01", "amount": 5},
        ["amount"],
    ),
    (
        "/depositCertificateSchedules",
        rest_certificates.deposit_certificate_schedules_all,
        "rest_certificates",
        {"cdId": 1, "transactionDate": "2026-01-01", "amount": 5},
        ["amount"],
    ),
]


class RouteTestCase(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.user = SimpleNamespace(id="1")
        for name, value in {
            "COUNTRIES": ["US"],
            "CURRENCIES": ["usd"],
        }.items():
            patcher = patch.object(Config, name, value, create=True)
            patcher.start()
            self.addCleanup(patcher.stop)

    def call(self, url, method, view, module, body, session, *args):
        with self.app.test_request_context(url, method=method, json=body), patch(
            f"routes.{module}.current_user", self.user
        ), patch(f"routes.{module}.reload_asset_store"), patch(
            f"routes.{module}.UserStore.get_user_config",
            return_value=SimpleNamespace(),
        ), patch.object(
            Config, "DB_SESSION", lambda: session, create=True
        ):
            return view.__wrapped__(*args)

    def assert_400(self, field, url, method, view, module, body, session):
        with self.assertRaises(HTTPError) as ctx:
            self.call(url, method, view, module, body, session)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn(field, ctx.exception.message)
        self.assertEqual(session.added, [])
        self.assertFalse(session.committed)


class TestPostsRejectBadNumbers(RouteTestCase):
    """Bad numeric input is a 400 and saves nothing, instead of a 500 later."""

    def test_bad_or_missing_numbers(self):
        for url, view, module, body, fields in POSTS:
            for field in fields:
                for value in ("abc", None, "nan", True):
                    with self.subTest(url=url, field=field, value=value):
                        self.assert_400(
                            field,
                            url,
                            "POST",
                            view,
                            module,
                            {**body, field: value},
                            SessionStub(),
                        )
                if field == "capital_rate":
                    continue  # defaults to 0 when left out
                with self.subTest(url=url, field=field, value="<missing>"):
                    payload = {k: v for k, v in body.items() if k != field}
                    self.assert_400(
                        field, url, "POST", view, module, payload, SessionStub()
                    )

    def test_missing_or_unknown_flow_class(self):
        for url, view, module, body, _ in POSTS:
            if "flowClass" not in body:
                continue
            for value in (None, "rent"):
                with self.subTest(url=url, value=value):
                    self.assert_400(
                        "flowClass",
                        url,
                        "POST",
                        view,
                        module,
                        {**body, "flowClass": value},
                        SessionStub(),
                    )

    def test_account_stores_validated_numbers(self):
        session = SessionStub()
        _, status = self.call(
            "/accounts",
            "POST",
            rest_assets.accounts,
            "rest_assets",
            {
                "id": "a",
                "country": "US",
                "currency": "usd",
                "balance": "1500",
                "factor": 1,
            },
            session,
        )
        self.assertEqual(status, 201)
        self.assertEqual(session.added[0].balance, "1500.0")
        self.assertEqual(session.added[0].factor, "1.0")

    def test_payable_stores_lower_case_flow_class(self):
        session = SessionStub({Account: QueryStub(first_item=None)})
        body = {**POSTS[2][3], "flowClass": "Transfer"}
        with patch("routes.rest_assets.validate_target_asset", return_value=True):
            _, status = self.call(
                "/payables", "POST", rest_assets.payables, "rest_assets", body, session
            )
        self.assertEqual(status, 201)
        self.assertEqual(session.added[0].flow_class, "transfer")
        self.assertEqual(session.added[0].balance, "10.0")


class TestPutsRejectBadNumbers(RouteTestCase):
    def put(self, url, view, module, model, existing, body, *args):
        session = SessionStub({model: QueryStub(first_item=existing)})
        with self.assertRaises(HTTPError) as ctx:
            self.call(url, "PUT", view, module, body, session, *args)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertFalse(session.committed)
        return ctx.exception.message

    def test_account_balance(self):
        existing = SimpleNamespace(
            id="a",
            country="US",
            currency="USD",
            balance="1",
            factor="1",
            institution="Bank",
            account_type="Checking",
            liquid=1,
            transfer_by=None,
            target_asset_id=None,
        )
        message = self.put(
            "/accounts/a",
            rest_assets.get_account,
            "rest_assets",
            rest_assets.Account,
            existing,
            {"balance": "abc"},
            "a",
        )
        self.assertIn("balance", message)

    def test_payable_unknown_flow_class(self):
        existing = SimpleNamespace(
            currency="USD",
            due_date="2030-01-01",
            amount="10",
            balance="10",
            flow_class="expense",
            target_asset_id="x",
        )
        message = self.put(
            "/payables/1",
            rest_assets.payables_get,
            "rest_assets",
            rest_assets.Payable,
            existing,
            {"flowClass": "rent"},
            1,
        )
        self.assertIn("flowClass", message)

    def test_recurrent_transaction_amount(self):
        existing = SimpleNamespace(
            parent_id="r",
            year_month="2026-01",
            paid_with="a",
            transaction_date="2026-01-02",
            description="",
            amount="-5",
        )
        message = self.put(
            "/recurrentTransactions/t",
            rest_recurrents.recurrent_transactions_get,
            "rest_recurrents",
            RecurrentTransaction,
            existing,
            {"amount": None},
            "t",
        )
        self.assertIn("amount", message)

    def test_recurrent_rate(self):
        existing = SimpleNamespace(
            recurrence="0 0 5 * *",
            target_asset_id="x",
            currency="USD",
            start="2026-01-01",
            end="2027-01-01",
            amount="-100",
            rate="0",
            flow_class="expense",
            country="US",
        )
        message = self.put(
            "/recurrents/r",
            rest_recurrents.recurrents_get,
            "rest_recurrents",
            Recurrent,
            existing,
            {"rate": "5%"},
            "r",
        )
        self.assertIn("rate", message)

    def test_bond_schedule_amount(self):
        existing = SimpleNamespace(date="2026-01-01", amount="5", paid=0)
        message = self.put(
            "/bondSchedules/1",
            rest_certificates.bond_schedules_get,
            "rest_certificates",
            rest_certificates.BondSchedule,
            existing,
            {"amount": ""},
            "1",
        )
        self.assertIn("amount", message)


class TestScheduleUploadRejectsBadAmount(RouteTestCase):
    def test_csv_amount(self):
        session = SessionStub()
        csv = "iid,date,amount,paid\n1,2026-01-01,12.5,0\n1,2026-02-01,abc,0\n"
        with self.app.test_request_context(
            "/bondSchedulesUpload", method="POST", data=csv
        ), patch("routes.rest_certificates.current_user", self.user), patch.object(
            Config, "DB_SESSION", lambda: session, create=True
        ), self.assertRaises(
            HTTPError
        ) as ctx:
            rest_certificates.bond_schedules_upload.__wrapped__()
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("amount", ctx.exception.message)
        self.assertFalse(session.committed)


if __name__ == "__main__":
    unittest.main()
