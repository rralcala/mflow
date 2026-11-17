"""An asset identifier is unique per user across every asset type: the routes
refuse duplicates with a 409, and unique indexes back them up."""

from http import HTTPStatus
from test.rest_dangling_test import AssetDbTestCase
from unittest.mock import patch

from apiflask import APIFlask
from sqlalchemy.exc import IntegrityError

from models.bond import Bond
from models.models import Account, Recurrent
from models.payable import Payable
from routes.assets import rest_assets, rest_certificates, rest_recurrents
from routes.errors import configure_errors

ACCOUNT = {
    "country": "US",
    "location": "Bank",
    "currency": "USD",
    "balance": 1,
    "factor": 1,
    "accountType": "checking",
}
INSTRUMENT = {
    "country": "US",
    "currency": "USD",
    "factor": 1,
    "qty": 1,
    "dividend": "N",
    "account": "A",
    "dividend_rate": 0,
    "acquisition_date": "2026-01-01",
    "acquisition_price": 1,
    "targetAssetId": "Checking",
}
PAYABLE = {
    "country": "US",
    "currency": "USD",
    "amount": -10,
    "balance": -10,
    "dueDate": "2027-01-01",
    "flowClass": "expense",
    "targetAssetId": "Checking",
}
PROPERTY = {
    "country": "US",
    "currency": "USD",
    "purchasePrice": 1,
    "purchaseDate": "2020-01-01",
    "currentPrice": 1,
    "rentPrice": 0,
    "depreciation": 0,
    "additionalData": "",
    "rentCurrency": "USD",
}
CERTIFICATE = {
    "capital": 1000,
    "currency": "USD",
    "maturityDate": "2030-01-01",
    "rate": 0.05,
    "entity": "Bank",
    "country": "US",
    "targetAssetId": "Checking",
}
RECURRENT = {
    "targetAssetId": "Checking",
    "country": "US",
    "amount": -10,
    "currency": "USD",
    "recurrence": "0 0 1 * *",
    "start": "2026-01-01",
    "end": "2030-01-01",
    "flowClass": "expense",
    "rate": 0,
}


class TestDuplicateIdentifiers(AssetDbTestCase):
    def post(self, view, body):
        return self.call(view, method="POST", json=body)

    def assertDuplicate(self, result, identifier):
        body, status = result
        self.assertEqual(status, HTTPStatus.CONFLICT)
        self.assertEqual(
            body["message"], f"An asset named '{identifier}' already exists"
        )

    def count(self, model, **filters):
        with self.Session() as session:
            return session.query(model).filter_by(**filters).count()

    # Creating

    def test_same_type_duplicates_are_refused(self):
        with patch.object(rest_assets, "instrument_symbol_error", return_value=None):
            self.assertDuplicate(
                self.post(
                    rest_assets.instrument_create,
                    dict(INSTRUMENT, location="Citi", symbol="VOO"),
                ),
                "Citi_A_VOO",
            )
        self.assertDuplicate(
            self.post(rest_assets.payable_create, dict(PAYABLE, description="Car tax")),
            "Car tax",
        )
        self.assertDuplicate(
            self.post(
                rest_assets.property_create, dict(PROPERTY, propertyName="House")
            ),
            "House",
        )
        self.assertDuplicate(
            self.post(rest_certificates.bond_create, dict(CERTIFICATE, name="BOND-A")),
            "BOND-A",
        )
        self.assertEqual(self.count(Payable, description="Car tax"), 1)
        self.assertEqual(self.count(Bond, name="BOND-A"), 1)

    def test_duplicate_primary_keys_in_own_account_are_409_not_500(self):
        self.assertDuplicate(
            self.post(rest_assets.account_create, dict(ACCOUNT, id="Checking")),
            "Checking",
        )
        self.assertDuplicate(
            self.post(rest_recurrents.recurrent_create, dict(RECURRENT, id="Food")),
            "Food",
        )

    def test_identifiers_are_unique_across_types(self):
        cases = [
            (rest_assets.account_create, dict(ACCOUNT, id="Car tax"), "Car tax"),
            (rest_assets.payable_create, dict(PAYABLE, description="House"), "House"),
            (
                rest_certificates.deposit_certificate_create,
                dict(CERTIFICATE, name="BOND-A"),
                "BOND-A",
            ),
            (
                rest_recurrents.recurrent_create,
                dict(RECURRENT, id="Citi_A_VOO"),
                "Citi_A_VOO",
            ),
        ]
        for view, body, identifier in cases:
            with self.subTest(identifier):
                self.assertDuplicate(self.post(view, body), identifier)

    def test_another_users_names_are_free_to_use(self):
        body, status = self.post(
            rest_certificates.bond_create, dict(CERTIFICATE, name="BOND-THEIRS")
        )
        self.assertEqual(status, HTTPStatus.CREATED, body)
        self.assertEqual(self.count(Bond, name="BOND-THEIRS"), 2)

    def test_another_users_account_and_recurrent_names_are_free_to_use(self):
        body, status = self.post(rest_assets.account_create, dict(ACCOUNT, id="Theirs"))
        self.assertEqual(status, HTTPStatus.CREATED, body)
        self.assertEqual(self.count(Account, id="Theirs"), 2)
        body, status = self.post(
            rest_recurrents.recurrent_create, dict(RECURRENT, id="TheirFood")
        )
        self.assertEqual(status, HTTPStatus.CREATED, body)
        self.assertEqual(self.count(Recurrent, identifier="TheirFood"), 2)

    # Renaming

    def test_renaming_onto_an_existing_identifier_is_refused(self):
        self.assertDuplicate(
            self.call(
                rest_assets.payable_update,
                1,
                method="PUT",
                json={"description": "House"},
            ),
            "House",
        )
        self.assertDuplicate(
            self.call(
                rest_certificates.deposit_certificate_update,
                1,
                method="PUT",
                json={"name": "BOND-A"},
            ),
            "BOND-A",
        )
        with self.Session() as session:
            self.assertEqual(session.get(Payable, 1).description, "Car tax")

    def test_saving_without_renaming_is_not_a_duplicate(self):
        body, status = self.call(
            rest_assets.payable_update,
            1,
            method="PUT",
            json={"description": "Car tax", "balance": -5},
        )
        self.assertEqual(status, HTTPStatus.OK, body)

    # The database backs the routes up

    def test_unique_index_rejects_a_duplicate_the_routes_missed(self):
        with self.Session() as session:
            payable = session.get(Payable, 1)
            session.add(
                Payable(
                    user_id=1,
                    country="US",
                    currency="USD",
                    description=payable.description,
                    amount="1",
                    due_date="2027-01-01",
                    commited=0,
                    balance="1",
                )
            )
            with self.assertRaises(IntegrityError):
                session.commit()


class TestIntegrityErrorResponse(AssetDbTestCase):
    def test_integrity_error_is_a_409_without_sql(self):
        app = APIFlask(__name__)
        configure_errors(app)

        @app.get("/boom")
        def boom():
            raise IntegrityError(
                "INSERT INTO payable ...", {}, Exception("UNIQUE constraint failed")
            )

        response = app.test_client().get("/boom")
        self.assertEqual(response.status_code, HTTPStatus.CONFLICT)
        self.assertEqual(
            response.get_json()["message"], "Conflicts with an existing record"
        )
        self.assertNotIn("INSERT", response.get_data(as_text=True))
