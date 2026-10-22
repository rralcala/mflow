import unittest
from test.numeric_validation_test import POSTS
from test.rest_assets_test import QueryStub, SessionStub, api_app, run_view
from types import SimpleNamespace
from unittest.mock import patch

from apiflask import HTTPError

from lib.config import REQUIRED_KEYS, Config, missing_required_keys
from lib.util import country_for_update, normalize_country
from models.models import Account
from routes.assets import rest_assets, rest_certificates, rest_recurrents

# Bodies that pass the input schemas, so a 400 is about the country alone.
VALID_BODIES = {url: body for url, _, _, body, _ in POSTS}
MISSING = object()


class CountryTestCase(unittest.TestCase):
    def setUp(self):
        self.app = api_app()
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

    def test_update_keeps_current_unless_changed(self):
        self.assertEqual(country_for_update({}, "XX"), "XX")
        # Unchanged legacy value does not block editing the record.
        self.assertEqual(country_for_update({"country": "XX"}, "XX"), "XX")
        self.assertEqual(country_for_update({"country": "us"}, "PY"), "US")
        with self.assertRaises(HTTPError):
            country_for_update({"country": "ZZ"}, "US")


class TestRequiredConfig(unittest.TestCase):
    def test_missing_or_malformed_countries_is_reported(self):
        self.assertEqual(REQUIRED_KEYS, ("COUNTRIES", "USERS"))
        users = {"USERS": ["1"]}
        self.assertEqual(missing_required_keys(SimpleNamespace(**users)), ["COUNTRIES"])
        self.assertEqual(
            missing_required_keys(SimpleNamespace(COUNTRIES="US", **users)),
            ["COUNTRIES"],
        )
        self.assertEqual(
            missing_required_keys(SimpleNamespace(COUNTRIES=["US"], **users)), []
        )

    def test_users_must_be_a_list(self):
        self.assertEqual(
            missing_required_keys(SimpleNamespace(COUNTRIES=[], USERS={"1": {}})),
            ["USERS"],
        )


class TestRoutesRejectBadCountry(CountryTestCase):
    """Bad country input must be a 400, not a 500."""

    def post(self, view, module, url, country=MISSING):
        body = {k: v for k, v in VALID_BODIES[url].items() if k != "country"}
        if country is not MISSING:
            body["country"] = country
        session = SessionStub({Account: QueryStub()})
        with self.app.test_request_context(url, method="POST", json=body), patch(
            f"routes.{module}.current_user", self.user
        ), patch.object(
            Config, "DB_SESSION", lambda: session, create=True
        ), patch.object(
            Config, "CURRENCIES", ["usd"], create=True
        ):
            response, status = run_view(view)
        self.assertEqual(session.added, [])
        return response, status

    def assert_400(self, *args):
        response, status = self.post(*args)
        self.assertEqual(status, 400)
        self.assertIn("ountry", response.get_json()["message"])

    def test_payable_missing_country(self):
        self.assert_400(rest_assets.payable_create, "rest_assets", "/payables")

    def test_payable_unknown_country(self):
        self.assert_400(rest_assets.payable_create, "rest_assets", "/payables", "ZZ")

    def test_certificate_non_string_country(self):
        self.assert_400(rest_certificates.bond_create, "rest_certificates", "/bonds", 7)

    def test_account_missing_country(self):
        # The account table's country column is NOT NULL.
        for country in (MISSING, None):
            with self.subTest(country=country):
                self.assert_400(
                    rest_assets.account_create, "rest_assets", "/accounts", country
                )

    def test_account_put_cannot_clear_country(self):
        existing = SimpleNamespace(id="a", country="US")
        session = SessionStub({Account: QueryStub(first_item=existing)})
        with self.app.test_request_context(
            "/accounts/a", method="PUT", json={"country": ""}
        ), patch("routes.rest_assets.current_user", self.user), patch.object(
            Config, "DB_SESSION", lambda: session, create=True
        ):
            response, status = run_view(rest_assets.account_update, "a")
        self.assertEqual(status, 400)
        self.assertIn("country", response.get_json()["message"])
        self.assertFalse(session.committed)

    def test_account_unknown_country(self):
        self.assert_400(rest_assets.account_create, "rest_assets", "/accounts", "ZZ")

    def test_recurrent_unknown_country(self):
        self.assert_400(
            rest_recurrents.recurrent_create, "rest_recurrents", "/recurrents", "ZZ"
        )

    def test_instrument_missing_country(self):
        self.assert_400(rest_assets.instrument_create, "rest_assets", "/instruments")

    def test_property_unknown_country(self):
        self.assert_400(rest_assets.property_create, "rest_assets", "/properties", "ZZ")


if __name__ == "__main__":
    unittest.main()
