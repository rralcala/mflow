import unittest
from test.rest_assets_test import QueryStub, SessionStub
from types import SimpleNamespace
from unittest.mock import patch

from apiflask import HTTPError
from flask import Flask

from lib.config import REQUIRED_KEYS, Config, missing_required_keys
from lib.util import country_for_update, normalize_country
from models.models import Account
from routes.assets import rest_assets, rest_certificates, rest_recurrents


class CountryTestCase(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.user = SimpleNamespace(id="1")
        countries = patch.object(Config, "COUNTRIES", ["US", "py"], create=True)
        countries.start()
        self.addCleanup(countries.stop)


class TestNormalizeCountry(CountryTestCase):
    def test_valid_codes_are_uppercased(self):
        self.assertEqual(normalize_country("us"), "US")
        self.assertEqual(normalize_country(" PY "), "PY")

    def test_invalid_input_is_a_400(self):
        for value in (None, "", "ZZ", 5, ["US"], {"a": 1}):
            with self.subTest(value=value), self.assertRaises(HTTPError) as ctx:
                normalize_country(value)
            self.assertEqual(ctx.exception.status_code, 400)

    def test_optional_allows_missing_but_not_unknown(self):
        self.assertIsNone(normalize_country(None, required=False))
        self.assertIsNone(normalize_country("", required=False))
        with self.assertRaises(HTTPError):
            normalize_country("ZZ", required=False)

    def test_update_keeps_current_unless_changed(self):
        self.assertEqual(country_for_update({}, "XX"), "XX")
        # Unchanged legacy value does not block editing the record.
        self.assertEqual(country_for_update({"country": "XX"}, "XX"), "XX")
        self.assertEqual(country_for_update({"country": "us"}, "PY"), "US")
        with self.assertRaises(HTTPError):
            country_for_update({"country": "ZZ"}, "US")


class TestRequiredConfig(unittest.TestCase):
    def test_missing_or_malformed_countries_is_reported(self):
        self.assertEqual(REQUIRED_KEYS, ("COUNTRIES",))
        self.assertEqual(missing_required_keys(SimpleNamespace()), ["COUNTRIES"])
        self.assertEqual(
            missing_required_keys(SimpleNamespace(COUNTRIES="US")), ["COUNTRIES"]
        )
        self.assertEqual(missing_required_keys(SimpleNamespace(COUNTRIES=["US"])), [])


class TestRoutesRejectBadCountry(CountryTestCase):
    """Bad country input must surface as HTTPError(400), not a 500."""

    def post(self, url, view, module, payload, **extra):
        session = SessionStub({Account: QueryStub()})
        with self.app.test_request_context(url, method="POST", json=payload), patch(
            f"routes.{module}.current_user", self.user
        ), patch.object(
            Config, "DB_SESSION", lambda: session, create=True
        ), patch.object(
            Config, "CURRENCIES", ["usd"], create=True
        ):
            view()
        return session

    def assert_400(self, *args, **kwargs):
        with self.assertRaises(HTTPError) as ctx:
            self.post(*args, **kwargs)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("ountry", ctx.exception.message)

    def test_payable_missing_country(self):
        self.assert_400(
            "/payables",
            rest_assets.payables.__wrapped__,
            "rest_assets",
            {"currency": "usd"},
        )

    def test_payable_unknown_country(self):
        self.assert_400(
            "/payables",
            rest_assets.payables.__wrapped__,
            "rest_assets",
            {"currency": "usd", "country": "ZZ"},
        )

    def test_certificate_non_string_country(self):
        self.assert_400(
            "/bonds",
            rest_certificates.bonds_all.__wrapped__,
            "rest_certificates",
            {"currency": "usd", "country": 7},
        )

    def test_account_unknown_country(self):
        self.assert_400(
            "/accounts",
            rest_assets.accounts.__wrapped__,
            "rest_assets",
            {"id": "a", "country": "ZZ"},
        )

    def test_recurrent_unknown_country(self):
        self.assert_400(
            "/recurrents",
            rest_recurrents.recurrents_all.__wrapped__,
            "rest_recurrents",
            {"id": "r", "country": "ZZ", "currency": "usd"},
        )

    def test_instrument_missing_country(self):
        self.assert_400(
            "/instruments",
            rest_assets.instruments.__wrapped__,
            "rest_assets",
            {"id": "i", "currency": "usd"},
        )

    def test_property_unknown_country(self):
        self.assert_400(
            "/properties",
            rest_assets.properties.__wrapped__,
            "rest_assets",
            {"id": "p", "country": "ZZ"},
        )


if __name__ == "__main__":
    unittest.main()
