import unittest
from types import SimpleNamespace
from unittest.mock import patch

from marshmallow import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from werkzeug.routing import UnicodeConverter

import routes.auth  # noqa: F401  registers login_manager's loaders, as service.py does
from data.base import Base
from init import create_app
from lib.config import Config
from lib.parsers import available_parsers
from lib.util import sha256_hash
from models.bond import Bond, BondSchedule
from models.deposit_certificate import DepositCertificate, DepositCertificateSchedule
from models.instrument import Instrument
from models.models import Account, Recurrent, RecurrentTransaction
from models.payable import Payable
from models.property import Property
from routes import register_api_routes
from routes import schemas as s
from routes.errors import validation_message


class TestOutputSchemasMatchModels(unittest.TestCase):
    """Output schemas drop keys they don't declare, so they must keep up with
    to_dict(): a field added to a model and not to its schema would vanish from
    the API."""

    def assert_round_trip(self, schema, data):
        self.assertEqual(set(schema().fields), set(data))
        self.assertEqual(schema().dump(data), data)

    def test_models(self):
        cases = [
            (
                s.AccountOut,
                Account(
                    id="Checking",
                    country="US",
                    institution="Bank",
                    currency="USD",
                    balance="10.0",
                    factor="1.0",
                    account_type="Checking",
                    liquid=1,
                    transfer_by="2030-01-01",
                    target_asset_id="Sweep_USD",
                ),
            ),
            (
                s.PayableOut,
                Payable(
                    id=1,
                    country="US",
                    currency="USD",
                    description="Tax",
                    amount="10.0",
                    due_date="2026-12-01",
                    commited=1,
                    balance="5.0",
                    flow_class="expense",
                    target_asset_id="Checking",
                ),
            ),
            (
                s.PropertyOut,
                Property(
                    id=1,
                    country="US",
                    currency="USD",
                    property_name="Flat",
                    purchase_price="100.0",
                    purchase_date="2020-01-01",
                    current_price="120.0",
                    rent_price="1.0",
                    depreciation="0.0",
                    additional_data="",
                    rent_currency="USD",
                    sell_by=None,
                    target_asset_id=None,
                ),
            ),
            (
                s.BondOut,
                Bond(
                    id=1,
                    name="B",
                    capital="100.0",
                    currency="USD",
                    maturity_date="2030-01-01",
                    rate="0.05",
                    entity="Bank",
                    country="US",
                    purchase_price="100.0",
                    target_asset_id="Checking",
                ),
            ),
            (
                s.DepositCertificateOut,
                DepositCertificate(
                    id=1,
                    name="CD",
                    capital="100.0",
                    currency="USD",
                    maturity_date="2030-01-01",
                    rate="0.05",
                    entity="Bank",
                    country="US",
                    purchase_price="100.0",
                    target_asset_id="Checking",
                ),
            ),
            (
                s.BondScheduleOut,
                BondSchedule(id=1, bond_id=2, date="2026-01-01", amount="5.0", paid=1),
            ),
            (
                s.DepositCertificateScheduleOut,
                DepositCertificateSchedule(
                    id=1, cd_id=2, date="2026-01-01", amount="5.0", paid=0
                ),
            ),
            (
                s.RecurrentOut,
                Recurrent(
                    identifier="Rent",
                    parent_asset_id=None,
                    target_asset_id="Checking",
                    country="US",
                    amount="-100.0",
                    currency="USD",
                    recurrence="0 0 5 * *",
                    start="2026-01-01",
                    end="2027-01-01",
                    flow_class="expense",
                    rate="0.0",
                    inflation=1,
                ),
            ),
        ]
        for schema, model in cases:
            with self.subTest(schema=schema.__name__):
                self.assert_round_trip(schema, model.to_dict())

    def test_instrument(self):
        instrument = Instrument(
            id=1,
            country="US",
            location="Broker",
            symbol="VOO",
            factor="1.0",
            qty="2.0",
            dividend="N",
            dividend_rate="0.0",
            currency="USD",
            acquisition_date="2026-01-01",
            acquisition_price="1.0",
            liquid=1,
            capital_rate="0.0",
            target_asset_id="Checking",
            sell_by=None,
            is_target_pool=0,
        )
        with patch("models.instrument.ExchangeRates.exchange_rate", return_value=5.0):
            self.assert_round_trip(s.InstrumentOut, instrument.to_dict())

    def test_recurrent_transaction_with_list_currency(self):
        transaction = RecurrentTransaction(
            transaction_id=1,
            parent_id="Rent",
            year_month="2026-01",
            description="January",
            amount="-100.0",
            transaction_date="2026-01-05",
            paid_with="Checking",
            create_date="2026-01-05 10:00:00",
            import_hash=None,
        )
        # The list adds the recurrent's currency to each transaction.
        self.assert_round_trip(
            s.RecurrentTransactionOut, {**transaction.to_dict(), "currency": "USD"}
        )

    def test_transaction_parsers(self):
        for parser in available_parsers().values():
            with self.subTest(parser=parser.id):
                self.assert_round_trip(s.TransactionParserOut, parser.to_dict())


class TestFields(unittest.TestCase):
    def test_dates_stay_strings(self):
        schema = s.AccountIn(partial=True)
        self.assertEqual(
            schema.load({"transferBy": "2030-01-31"}), {"transferBy": "2030-01-31"}
        )
        for bad in ("2030-02-30", "01/31/2030", "2030-1-31x", 20300131):
            with self.subTest(value=bad), self.assertRaises(ValidationError) as ctx:
                schema.load({"transferBy": bad})
            self.assertEqual(
                ctx.exception.messages,
                {"transferBy": ["Not a valid date, expected YYYY-MM-DD."]},
            )

    def test_blank_optional_values_load_as_none(self):
        # A cleared date input is sent as "", which the routes store as NULL.
        self.assertEqual(
            s.AccountIn(partial=True).load({"transferBy": ""}), {"transferBy": None}
        )
        self.assertEqual(
            s.RecurrentHistoryQuery().load({"startYearMonth": ""}),
            {"startYearMonth": None},
        )
        # A required date can't be blank.
        with self.assertRaises(ValidationError):
            s.PayableIn(partial=True).load({"dueDate": ""})

    def test_year_month(self):
        schema = s.RecurrentTransactionIn(partial=True)
        self.assertEqual(
            schema.load({"yearMonth": "2026-12"}), {"yearMonth": "2026-12"}
        )
        for bad in ("2026-13", "2026-1", "2026-01-01"):
            with self.subTest(value=bad), self.assertRaises(ValidationError):
                schema.load({"yearMonth": bad})

    def test_numbers_reject_booleans_and_nan(self):
        schema = s.AccountIn(partial=True)
        self.assertEqual(schema.load({"balance": "12.5"}), {"balance": 12.5})
        for bad in (True, "nan", "inf", "abc", None):
            with self.subTest(value=bad), self.assertRaises(ValidationError):
                schema.load({"balance": bad})

    def test_unknown_fields_are_dropped(self):
        # react-admin sends whole records back, read-only fields included.
        loaded = s.InstrumentIn(partial=True).load(
            {"qty": 2, "value": 99.0, "estimated_dividend": 1.0, "user_id": 2}
        )
        self.assertEqual(loaded, {"qty": 2.0})

    def test_update_schema_requires_nothing(self):
        self.assertEqual(s.RecurrentIn(partial=True, exclude=("id",)).load({}), {})
        with self.assertRaises(ValidationError) as ctx:
            s.RecurrentIn().load({})
        self.assertIn("id", ctx.exception.messages)


class TestValidationMessage(unittest.TestCase):
    def test_names_each_field(self):
        detail = {
            "json": {
                "balance": ["Not a valid number."],
                "currency": ["Missing data for required field."],
            }
        }
        self.assertEqual(
            validation_message(detail),
            "balance: Not a valid number.; currency: Missing data for required field.",
        )

    def test_nested_and_schema_errors(self):
        self.assertEqual(
            validation_message(
                {"json": {"transactions": {0: {"amount": ["Not a valid number."]}}}}
            ),
            "transactions.0.amount: Not a valid number.",
        )
        self.assertEqual(
            validation_message({"json": {"_schema": ["Invalid input type."]}}),
            "Invalid input type.",
        )


def api(debug=False):
    """The real app with every blueprint registered."""
    app = create_app(debug=debug)
    # service.py registers the real converter; any string will do here.
    app.url_map.converters["identifier"] = UnicodeConverter
    register_api_routes(app)
    return app


class AppTestCase(unittest.TestCase):
    def setUp(self):
        for name, value in {
            "SECRET_KEY": "unit-test-secret-key-at-least-32-bytes-long",
            "USERS": {
                "1": {
                    "username": "jdoe",
                    "name": "J Doe",
                    "password": sha256_hash("pw"),
                    "email": "jdoe@example.com",
                }
            },
            "COUNTRIES": ["US"],
            "CURRENCIES": ["usd"],
        }.items():
            patcher = patch.object(Config, name, value, create=True)
            patcher.start()
            self.addCleanup(patcher.stop)


class TestOpenApiSpec(AppTestCase):
    # Bodies that aren't JSON objects: CSV text and a multipart upload.
    NON_JSON_BODIES = {
        "/assets/bondSchedulesUpload",
        "/assets/cdSchedulesUpload",
    }
    # Reports whose payloads don't have output schemas yet (see TODO.md).
    UNDOCUMENTED_RESPONSES = {
        "/reports/assets_by_location",
        "/reports/cash_flow",
        "/reports/future_timeline",
        "/reports/income_per_location",
        "/reports/investment_performance",
        "/reports/monthly_pnl",
        "/reports/nw_summary",
        "/reports/recurrent_history",
        "/reports/spending_analysis",
        "/reports/valuation_history",
    }

    def setUp(self):
        super().setUp()
        self.spec = api(debug=True).test_client().get("/openapi.json").get_json()

    def operations(self):
        for path, item in self.spec["paths"].items():
            for method, operation in item.items():
                yield path, method, operation

    def test_writes_document_their_body(self):
        for path, method, operation in self.operations():
            if method in ("post", "put") and path not in self.NON_JSON_BODIES:
                with self.subTest(path=path, method=method):
                    self.assertIn("requestBody", operation)

    def test_responses_have_schemas(self):
        for path, method, operation in self.operations():
            if path in self.UNDOCUMENTED_RESPONSES:
                continue
            with self.subTest(path=path, method=method):
                success = [
                    response
                    for status, response in operation["responses"].items()
                    if status.startswith("2")
                ]
                self.assertEqual(len(success), 1)
                content = success[0]["content"]
                self.assertTrue(
                    any(media.get("schema") for media in content.values()), content
                )

    def test_lists_document_total_count(self):
        get = self.spec["paths"]["/assets/accounts"]["get"]
        self.assertIn("X-Total-Count", get["responses"]["200"]["headers"])
        self.assertEqual(
            [p["name"] for p in get["parameters"]],
            ["_start", "_end", "_sort", "_order"],
        )
        body = get["responses"]["200"]["content"]["application/json"]["schema"]
        self.assertEqual(body["type"], "array")

    def test_create_and_update_bodies(self):
        account = self.spec["paths"]["/assets/accounts"]["post"]
        self.assertIn("201", account["responses"])
        schemas = self.spec["components"]["schemas"]
        self.assertIn("balance", schemas["AccountIn"]["required"])
        # Updates are partial: a field left out keeps its stored value.
        self.assertNotIn("required", schemas["AccountInUpdate"])
        self.assertNotIn("id", schemas["AccountInUpdate"]["properties"])


class TestEndToEnd(AppTestCase):
    """Requests through the real app: auth, schemas and error bodies together."""

    def setUp(self):
        super().setUp()
        engine = create_engine("sqlite://")
        self.addCleanup(engine.dispose)
        Base.metadata.create_all(engine, tables=[Account.__table__])
        for patcher in (
            patch.object(Config, "DB_SESSION", sessionmaker(bind=engine), create=True),
            patch("routes.assets.rest_assets.reload_asset_store"),
            patch("routes.assets.rest_assets.UserStore.get_user_config"),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.client = api().test_client()
        self.account = {
            "id": "Checking",
            "country": "us",
            "institution": "Bank",
            "currency": "usd",
            "balance": "100",
            "factor": 1,
            "accountType": "Checking",
            "liquid": True,
        }

    def login(self):
        response = self.client.post(
            "/auth/rlogin", json={"username": "jdoe", "password": "pw"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"id": "1", "fullName": "jdoe"})

    def test_auth_comes_before_validation(self):
        response = self.client.post("/assets/accounts", json={"balance": "abc"})
        self.assertEqual(response.status_code, 401)

    def test_login_body_is_validated(self):
        response = self.client.post("/auth/rlogin", json={"username": "jdoe"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json()["message"],
            "password: Missing data for required field.",
        )

    def test_validation_error(self):
        self.login()
        response = self.client.post(
            "/assets/accounts", json={**self.account, "balance": "abc"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json(),
            {
                "message": "balance: Not a valid number.",
                "detail": {"json": {"balance": ["Not a valid number."]}},
            },
        )

    def test_create_list_update(self):
        self.login()
        response = self.client.post("/assets/accounts", json=self.account)
        self.assertEqual(response.status_code, 201)
        created = response.get_json()
        self.assertEqual((created["balance"], created["currency"]), (100.0, "USD"))

        response = self.client.get("/assets/accounts?_start=0&_end=10")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Total-Count"], "1")
        self.assertEqual(response.get_json(), [created])

        # react-admin sends the whole record back; only balance changed.
        response = self.client.put(
            "/assets/accounts/Checking", json={**created, "balance": 50}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {**created, "balance": 50.0})

    def test_not_found(self):
        self.login()
        response = self.client.get("/assets/accounts/Nope")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["message"], "Account not found")

    def test_bad_query_argument(self):
        self.login()
        response = self.client.get("/assets/accounts?_start=-1")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json()["message"],
            "_start: Must be greater than or equal to 0.",
        )


if __name__ == "__main__":
    unittest.main()
