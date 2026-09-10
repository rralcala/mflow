import unittest
from http import HTTPStatus
from types import SimpleNamespace
from unittest.mock import patch

from flask import Flask

from lib.config import Config
from models.models import Recurrent, RecurrentTransaction
from routes.assets import rest_assets, rest_certificates, rest_recurrents


def row(data):
    return SimpleNamespace(to_dict=lambda data=data: data)


class QueryStub:
    def __init__(self, all_items=None, first_item=None, scalar_value=None):
        self._all_items = all_items or []
        self._first_item = first_item
        self._scalar_value = scalar_value

    def filter_by(self, **kwargs):
        return self

    def filter(self, *args):
        return self

    def order_by(self, *args):
        return self

    def all(self):
        return self._all_items

    def first(self):
        return self._first_item

    def scalar(self):
        return self._scalar_value


class SessionStub:
    def __init__(self, query_map=None):
        self.query_map = query_map or {}
        self.added = []
        self.deleted = []
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def query(self, model):
        return self.query_map.get(model, QueryStub())

    def add(self, item):
        self.added.append(item)

    def delete(self, item):
        self.deleted.append(item)

    def commit(self):
        self.committed = True


class TestRestAssetsRoutes(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.user = SimpleNamespace(id="1")

    def test_accounts_get(self):
        session = SessionStub(
            {
                rest_assets.Account: QueryStub(
                    all_items=[
                        row({"id": "b", "balance": 20}),
                        row({"id": "a", "balance": 10}),
                    ]
                )
            }
        )
        with self.app.test_request_context(
            "/accounts?_sort=id&_order=ASC&_start=0&_end=1", method="GET"
        ), patch("routes.rest_assets.current_user", self.user), patch.object(
            Config, "DB_SESSION", lambda: session, create=True
        ):
            response, status = rest_assets.accounts.__wrapped__()

        self.assertEqual(status, 200)
        self.assertEqual(response.headers["X-Total-Count"], "2")
        self.assertEqual(response.get_json(), [{"id": "a", "balance": 10}])

    def test_asset_get_found(self):
        asset = SimpleNamespace(identifier="asset-1")
        with self.app.test_request_context("/assets/asset-1", method="GET"), patch(
            "routes.rest_assets.current_user", self.user
        ), patch(
            "routes.rest_assets.UserStore.get_user_config",
            return_value=SimpleNamespace(),
        ), patch(
            "routes.rest_assets.get_asset_store", return_value={"bucket": [asset]}
        ), patch(
            "routes.rest_assets.asset_data_from_asset", return_value={"id": "asset-1"}
        ):
            response, status = rest_assets.asset_get.__wrapped__("asset-1")

        self.assertEqual(status, 200)
        self.assertEqual(response.get_json(), {"id": "asset-1"})

    def test_assets_get(self):
        with self.app.test_request_context(
            "/assets?liquid=true&id=a&id=c&_sort=id&_order=DESC&_start=0&_end=1",
            method="GET",
        ), patch("routes.rest_assets.current_user", self.user), patch(
            "routes.rest_assets.UserStore.get_user_config",
            return_value=SimpleNamespace(),
        ), patch(
            "routes.rest_assets.get_asset_store", return_value={}
        ), patch(
            "routes.rest_assets.get_assets",
            return_value=[
                {"id": "a", "name": "A"},
                {"id": "b", "name": "B"},
                {"id": "c", "name": "C"},
            ],
        ):
            response, status = rest_assets.assets.__wrapped__()

        self.assertEqual(status, 200)
        self.assertEqual(response.headers["X-Total-Count"], "2")
        self.assertEqual(response.get_json(), [{"id": "c", "name": "C"}])

    def test_bond_schedules_all_get(self):
        session = SessionStub(
            {
                rest_certificates.BondSchedule: QueryStub(
                    all_items=[row({"id": "1"}), row({"id": "2"})]
                )
            }
        )
        with self.app.test_request_context("/bondSchedules", method="GET"), patch(
            "routes.rest_certificates.current_user", self.user
        ), patch.object(Config, "DB_SESSION", lambda: session, create=True):
            response, status = rest_certificates.bond_schedules_all.__wrapped__()

        self.assertEqual(status, 200)
        self.assertEqual(response.headers["X-Total-Count"], "2")

    def test_bond_schedules_get_not_found(self):
        session = SessionStub(
            {rest_certificates.BondSchedule: QueryStub(first_item=None)}
        )
        with self.app.test_request_context("/bondSchedules/1", method="GET"), patch(
            "routes.rest_certificates.current_user", self.user
        ), patch.object(Config, "DB_SESSION", lambda: session, create=True):
            response, status = rest_certificates.bond_schedules_get.__wrapped__("1")

        self.assertEqual(status, 404)
        self.assertEqual(response.get_json(), {"message": "Bond Schedule not found"})

    def test_bonds_all_get(self):
        session = SessionStub(
            {
                rest_certificates.Bond: QueryStub(
                    all_items=[
                        row({"id": "a", "name": "a"}),
                        row({"id": "b", "name": "b"}),
                    ]
                )
            }
        )
        with self.app.test_request_context("/bonds", method="GET"), patch(
            "routes.rest_certificates.current_user", self.user
        ), patch.object(Config, "DB_SESSION", lambda: session, create=True):
            response, status = rest_certificates.bonds_all.__wrapped__()

        self.assertEqual(status, 200)
        self.assertEqual(
            response.get_json(), [{"id": "a", "name": "a"}, {"id": "b", "name": "b"}]
        )

    def test_bonds_get_not_found(self):
        session = SessionStub({rest_certificates.Bond: QueryStub(first_item=None)})
        with self.app.test_request_context("/bonds/1", method="GET"), patch(
            "routes.rest_certificates.current_user", self.user
        ), patch.object(Config, "DB_SESSION", lambda: session, create=True):
            response, status = rest_certificates.bonds_get.__wrapped__("1")

        self.assertEqual(status, 404)
        self.assertEqual(response.get_json(), {"message": "Bond not found"})

    def test_deposit_certificate_schedules_all_get(self):
        session = SessionStub(
            {
                rest_certificates.DepositCertificateSchedule: QueryStub(
                    all_items=[row({"id": "1"})]
                )
            }
        )
        with self.app.test_request_context(
            "/depositCertificateSchedules", method="GET"
        ), patch("routes.rest_certificates.current_user", self.user), patch.object(
            Config, "DB_SESSION", lambda: session, create=True
        ):
            response, status = (
                rest_certificates.deposit_certificate_schedules_all.__wrapped__()
            )

        self.assertEqual(status, 200)
        self.assertEqual(response.headers["X-Total-Count"], "1")

    def test_deposit_certificate_schedules_get_not_found(self):
        session = SessionStub(
            {rest_certificates.DepositCertificateSchedule: QueryStub(first_item=None)}
        )
        with self.app.test_request_context(
            "/depositCertificateSchedules/1", method="GET"
        ), patch("routes.rest_certificates.current_user", self.user), patch.object(
            Config, "DB_SESSION", lambda: session, create=True
        ):
            response, status = (
                rest_certificates.deposit_certificate_schedules_get.__wrapped__("1")
            )

        self.assertEqual(status, 404)

    def test_deposit_certificates_all_get(self):
        session = SessionStub(
            {
                rest_certificates.DepositCertificate: QueryStub(
                    all_items=[
                        row({"id": "2", "name": "a"}),
                        row({"id": "1", "name": "b"}),
                    ]
                )
            }
        )
        with self.app.test_request_context("/depositCertificates", method="GET"), patch(
            "routes.rest_certificates.current_user", self.user
        ), patch.object(Config, "DB_SESSION", lambda: session, create=True):
            response, status = rest_certificates.deposit_certificates_all.__wrapped__()

        self.assertEqual(status, 200)
        self.assertEqual(
            response.get_json(), [{"id": "2", "name": "a"}, {"id": "1", "name": "b"}]
        )

    def test_deposit_certificates_get_not_found(self):
        session = SessionStub(
            {rest_certificates.DepositCertificate: QueryStub(first_item=None)}
        )
        with self.app.test_request_context(
            "/depositCertificates/1", method="GET"
        ), patch("routes.rest_certificates.current_user", self.user), patch.object(
            Config, "DB_SESSION", lambda: session, create=True
        ):
            response, status = rest_certificates.deposit_certificates_get.__wrapped__(
                "1"
            )

        self.assertEqual(status, 404)

    def test_get_account_not_found(self):
        session = SessionStub({rest_assets.Account: QueryStub(first_item=None)})
        with self.app.test_request_context("/accounts/acc", method="GET"), patch(
            "routes.rest_assets.current_user", self.user
        ), patch.object(Config, "DB_SESSION", lambda: session, create=True):
            response, status = rest_assets.get_account.__wrapped__("acc")

        self.assertEqual(status, 404)

    def test_instruments_get_collection(self):
        session = SessionStub(
            {
                rest_assets.Instrument: QueryStub(
                    all_items=[
                        row({"id": 2, "location": "NYSE"}),
                        row({"id": 1, "location": "NASDAQ"}),
                    ]
                )
            }
        )
        with self.app.test_request_context(
            "/instruments?_sort=id&_order=ASC&_start=0&_end=1", method="GET"
        ), patch("routes.rest_assets.current_user", self.user), patch.object(
            Config, "DB_SESSION", lambda: session, create=True
        ):
            response, status = rest_assets.instruments.__wrapped__()

        self.assertEqual(status, 200)
        self.assertEqual(response.get_json(), [{"id": 1, "location": "NASDAQ"}])

    def test_instruments_get_not_found(self):
        session = SessionStub({rest_assets.Instrument: QueryStub(first_item=None)})
        with self.app.test_request_context("/instruments/1", method="GET"), patch(
            "routes.rest_assets.current_user", self.user
        ), patch.object(Config, "DB_SESSION", lambda: session, create=True):
            response, status = rest_assets.instruments_get.__wrapped__(1)

        self.assertEqual(status, 404)

    def test_load_tx(self):
        months = [
            (
                "2026-04",
                [
                    {
                        "id": "t1",
                        "assetId": "a1",
                        "amount": -10.0,
                        "currency": "USD",
                    }
                ],
            ),
            (
                "2026-05",
                [
                    {
                        "id": "t2",
                        "assetId": "a2",
                        "amount": 5.0,
                        "currency": "USD",
                    }
                ],
            ),
        ]
        with self.app.test_request_context("/monthlyTransactions", method="GET"), patch(
            "routes.rest_assets.current_user", self.user
        ), patch(
            "routes.rest_assets.UserStore.get_user_config",
            return_value=SimpleNamespace(),
        ), patch(
            "routes.rest_assets.get_asset_store", return_value={}
        ), patch(
            "routes.rest_assets.upcoming_monthly_transactions", return_value=months
        ):
            result = rest_assets.load_tx()

        self.assertEqual(result[0]["yearMonth"], "2026-04")
        self.assertEqual(result[1]["yearMonth"], "2026-05")

    def test_monthly_transactions(self):
        with self.app.test_request_context("/monthlyTransactions", method="GET"), patch(
            "routes.rest_assets.current_user", self.user
        ), patch(
            "routes.rest_assets.load_tx",
            return_value=[
                {"id": "neg", "amount": -1.0},
                {"id": "pos", "amount": 1.0},
            ],
        ):
            response = rest_assets.monthly_transactions.__wrapped__()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [{"id": "neg", "amount": -1.0}])

    def test_monthly_transactions_get_found(self):
        with self.app.test_request_context(
            "/monthlyTransactions/neg", method="GET"
        ), patch("routes.rest_assets.current_user", self.user), patch(
            "routes.rest_assets.load_tx", return_value=[{"id": "neg", "amount": -1.0}]
        ):
            response = rest_assets.monthly_transactions_get.__wrapped__("neg")

        self.assertEqual(response.status_code, 200)

    def test_payables_get_collection(self):
        session = SessionStub(
            {
                rest_assets.Payable: QueryStub(
                    all_items=[
                        row({"id": 2, "dueDate": "2026-02-01"}),
                        row({"id": 1, "dueDate": "2026-01-01"}),
                    ]
                )
            }
        )
        with self.app.test_request_context(
            "/payables?_sort=id&_order=DESC&_start=0&_end=1", method="GET"
        ), patch("routes.rest_assets.current_user", self.user), patch.object(
            Config, "DB_SESSION", lambda: session, create=True
        ):
            response, status = rest_assets.payables.__wrapped__()

        self.assertEqual(status, 200)
        self.assertEqual(response.headers["X-Total-Count"], "2")
        self.assertEqual(response.get_json(), [{"id": 2, "dueDate": "2026-02-01"}])

    def test_payables_get_not_found(self):
        session = SessionStub({rest_assets.Payable: QueryStub(first_item=None)})
        with self.app.test_request_context("/payables/1", method="GET"), patch(
            "routes.rest_assets.current_user", self.user
        ), patch.object(Config, "DB_SESSION", lambda: session, create=True):
            response, status = rest_assets.payables_get.__wrapped__(1)

        self.assertEqual(status, 404)

    def test_properties_get_collection(self):
        session = SessionStub(
            {
                rest_assets.Property: QueryStub(
                    all_items=[
                        row({"id": 2, "propertyName": "Z"}),
                        row({"id": 1, "propertyName": "A"}),
                    ]
                )
            }
        )
        with self.app.test_request_context(
            "/properties?_sort=propertyName&_order=ASC&_start=0&_end=1", method="GET"
        ), patch("routes.rest_assets.current_user", self.user), patch.object(
            Config, "DB_SESSION", lambda: session, create=True
        ):
            response, status = rest_assets.properties.__wrapped__()

        self.assertEqual(status, 200)
        self.assertEqual(response.get_json(), [{"id": 1, "propertyName": "A"}])

    def test_properties_get_not_found(self):
        session = SessionStub({rest_assets.Property: QueryStub(first_item=None)})
        with self.app.test_request_context("/properties/1", method="GET"), patch(
            "routes.rest_assets.current_user", self.user
        ), patch.object(Config, "DB_SESSION", lambda: session, create=True):
            response, status = rest_assets.properties_get.__wrapped__(1)

        self.assertEqual(status, 404)

    def test_recurrent_transactions_get_collection(self):
        recurrent_rows = [
            SimpleNamespace(
                identifier="r1", to_dict=lambda: {"id": "r1", "currency": "USD"}
            )
        ]
        transaction_rows = [
            SimpleNamespace(
                parent_id="r1",
                to_dict=lambda: {
                    "transactionId": "t1",
                    "recurrentId": "r1",
                    "amount": 12.0,
                },
            )
        ]
        session = SessionStub(
            {
                Recurrent: QueryStub(all_items=recurrent_rows),
                RecurrentTransaction: QueryStub(all_items=transaction_rows),
            }
        )

        with self.app.test_request_context(
            "/recurrentTransactions", method="GET"
        ), patch("routes.rest_recurrents.current_user", self.user), patch.object(
            Config, "DB_SESSION", lambda: session, create=True
        ):
            response, status = rest_recurrents.recurrent_transactions.__wrapped__()

        self.assertEqual(status, 200)
        self.assertEqual(response.get_json()[0]["currency"], "USD")

    def test_recurrent_transactions_get_not_found(self):
        session = SessionStub({RecurrentTransaction: QueryStub(first_item=None)})
        with self.app.test_request_context(
            "/recurrentTransactions/missing", method="GET"
        ), patch("routes.rest_recurrents.current_user", self.user), patch.object(
            Config, "DB_SESSION", lambda: session, create=True
        ):
            response, status = rest_recurrents.recurrent_transactions_get.__wrapped__(
                "missing"
            )

        self.assertEqual(status, 404)

    def test_recurrents_all_get(self):
        session = SessionStub(
            {Recurrent: QueryStub(all_items=[row({"id": "b"}), row({"id": "a"})])}
        )
        with self.app.test_request_context("/recurrents", method="GET"), patch(
            "routes.rest_recurrents.current_user", self.user
        ), patch.object(Config, "DB_SESSION", lambda: session, create=True):
            response, status = rest_recurrents.recurrents_all.__wrapped__()

        self.assertEqual(status, 200)
        self.assertEqual(response.get_json(), [{"id": "a"}, {"id": "b"}])

    def test_recurrents_get_not_found(self):
        session = SessionStub({Recurrent: QueryStub(first_item=None)})
        with self.app.test_request_context("/recurrents/r", method="GET"), patch(
            "routes.rest_recurrents.current_user", self.user
        ), patch.object(Config, "DB_SESSION", lambda: session, create=True):
            response, status = rest_recurrents.recurrents_get.__wrapped__("r")

        self.assertEqual(status, 404)

    def test_certificates_all_post_success_with_account_target(self):
        session = SessionStub(
            {
                rest_assets.Account: QueryStub(first_item=SimpleNamespace(id="acc-1")),
            }
        )
        with self.app.test_request_context(
            "/bonds",
            method="POST",
            json={
                "name": "b1",
                "capital": 100.0,
                "rate": 0.05,
                "maturityDate": "2030-01-01",
                "currency": "usd",
                "entity": "Bank",
                "country": "us",
                "targetAssetId": "acc-1",
            },
        ), patch("routes.rest_certificates.current_user", self.user), patch(
            "routes.rest_certificates.reload_asset_store"
        ), patch(
            "routes.rest_certificates.UserStore.get_user_config",
            return_value=SimpleNamespace(),
        ), patch.object(
            Config, "DB_SESSION", lambda: session, create=True
        ), patch.object(Config, "CURRENCIES", ["usd"], create=True), patch.object(
            Config, "COUNTRIES", ["US"], create=True
        ):
            response, status = rest_certificates.bonds_all.__wrapped__()

        self.assertEqual(status, 201)
        self.assertEqual(len(session.added), 1)
        self.assertEqual(session.added[0].target_asset_id, "acc-1")

    def test_certificates_all_post_bad_target(self):
        session = SessionStub(
            {
                rest_assets.Account: QueryStub(first_item=None),
                rest_assets.Instrument: QueryStub(first_item=None),
            }
        )
        with self.app.test_request_context(
            "/bonds",
            method="POST",
            json={
                "name": "b1",
                "capital": 100.0,
                "rate": 0.05,
                "maturityDate": "2030-01-01",
                "currency": "usd",
                "entity": "Bank",
                "country": "us",
                "targetAssetId": "missing",
            },
        ), patch("routes.rest_certificates.current_user", self.user), patch.object(
            Config, "DB_SESSION", lambda: session, create=True
        ), patch.object(Config, "CURRENCIES", ["usd"], create=True), patch.object(
            Config, "COUNTRIES", ["US"], create=True
        ):
            response, status = rest_certificates.bonds_all.__wrapped__()

        self.assertEqual(status, HTTPStatus.BAD_REQUEST)
        self.assertEqual(response.get_json(), {"message": "Bad target asset"})
        self.assertEqual(session.added, [])

    def test_certificate_get_put_bad_target(self):
        existing = SimpleNamespace(target_asset_id="old", name="b1")
        session = SessionStub(
            {
                rest_certificates.Bond: QueryStub(first_item=existing),
                rest_assets.Account: QueryStub(first_item=None),
                rest_assets.Instrument: QueryStub(first_item=None),
            }
        )
        with self.app.test_request_context(
            "/bonds/1", method="PUT", json={"targetAssetId": "missing"}
        ), patch("routes.rest_certificates.current_user", self.user), patch.object(
            Config, "DB_SESSION", lambda: session, create=True
        ):
            response, status = rest_certificates.bonds_get.__wrapped__("1")

        self.assertEqual(status, HTTPStatus.BAD_REQUEST)
        self.assertEqual(response.get_json(), {"message": "Bad target asset"})
        self.assertFalse(session.committed)

    def test_recurrents_all_post_bad_target(self):
        session = SessionStub(
            {
                rest_assets.Account: QueryStub(first_item=None),
                rest_assets.Instrument: QueryStub(first_item=None),
            }
        )
        with self.app.test_request_context(
            "/recurrents",
            method="POST",
            json={
                "id": "r1",
                "country": "US",
                "amount": 10.0,
                "currency": "USD",
                "recurrence": "0 0 1 * *",
                "start": "2026-01-01",
                "end": "2027-01-01",
                "flowClass": "Expense",
                "rate": 0.0,
                "targetAssetId": "missing",
            },
        ), patch("routes.rest_recurrents.current_user", self.user), patch.object(
            Config, "DB_SESSION", lambda: session, create=True
        ):
            response, status = rest_recurrents.recurrents_all.__wrapped__()

        self.assertEqual(status, HTTPStatus.BAD_REQUEST)
        self.assertEqual(response.get_json(), {"message": "Bad target asset"})
        self.assertEqual(session.added, [])

    def test_recurrents_all_post_success_with_instrument_target(self):
        session = SessionStub(
            {
                rest_assets.Account: QueryStub(first_item=None),
                rest_assets.Instrument: QueryStub(first_item=SimpleNamespace(id=7)),
            }
        )
        with self.app.test_request_context(
            "/recurrents",
            method="POST",
            json={
                "id": "r1",
                "country": "US",
                "amount": 10.0,
                "currency": "USD",
                "recurrence": "0 0 1 * *",
                "start": "2026-01-01",
                "end": "2027-01-01",
                "flowClass": "Income",
                "rate": 0.0,
                "targetAssetId": "7",
            },
        ), patch("routes.rest_recurrents.current_user", self.user), patch(
            "routes.rest_recurrents.reload_asset_store"
        ), patch(
            "routes.rest_recurrents.UserStore.get_user_config",
            return_value=SimpleNamespace(),
        ), patch.object(Config, "DB_SESSION", lambda: session, create=True):
            response, status = rest_recurrents.recurrents_all.__wrapped__()

        self.assertEqual(status, 201)
        self.assertEqual(session.added[0].target_asset_id, "7")

    def test_recurrents_get_put_bad_target(self):
        existing = SimpleNamespace(
            target_asset_id="old", parent_asset_id="parent-1", identifier="r1"
        )
        session = SessionStub(
            {
                Recurrent: QueryStub(first_item=existing),
                rest_assets.Account: QueryStub(first_item=None),
                rest_assets.Instrument: QueryStub(first_item=None),
            }
        )
        with self.app.test_request_context(
            "/recurrents/r1", method="PUT", json={"targetAssetId": "missing"}
        ), patch("routes.rest_recurrents.current_user", self.user), patch.object(
            Config, "DB_SESSION", lambda: session, create=True
        ):
            response, status = rest_recurrents.recurrents_get.__wrapped__("r1")

        self.assertEqual(status, HTTPStatus.BAD_REQUEST)
        self.assertEqual(response.get_json(), {"message": "Bad target asset"})
        self.assertFalse(session.committed)

    def test_instruments_post_bad_target(self):
        session = SessionStub(
            {
                rest_assets.Account: QueryStub(first_item=None),
                rest_assets.Instrument: QueryStub(first_item=None),
            }
        )
        with self.app.test_request_context(
            "/instruments",
            method="POST",
            json={
                "country": "US",
                "location": "NYSE",
                "symbol": "AAPL",
                "currency": "USD",
                "factor": 1.0,
                "qty": 1,
                "dividend": "",
                "dividend_rate": 0.0,
                "acquisition_date": "2026-01-01",
                "acquisition_price": 100.0,
                "liquid": True,
                "targetAssetId": "missing",
            },
        ), patch("routes.rest_assets.current_user", self.user), patch.object(
            Config, "DB_SESSION", lambda: session, create=True
        ):
            response, status = rest_assets.instruments.__wrapped__()

        self.assertEqual(status, HTTPStatus.BAD_REQUEST)
        self.assertEqual(session.added, [])

    def test_instruments_get_put_bad_target(self):
        existing = SimpleNamespace(target_asset_id="old")
        session = SessionStub(
            {
                rest_assets.Instrument: QueryStub(first_item=existing),
                rest_assets.Account: QueryStub(first_item=None),
            }
        )
        with self.app.test_request_context(
            "/instruments/1",
            method="PUT",
            json={"acquisition_date": "2026-01-01", "targetAssetId": "missing"},
        ), patch("routes.rest_assets.current_user", self.user), patch.object(
            Config, "DB_SESSION", lambda: session, create=True
        ):
            response, status = rest_assets.instruments_get.__wrapped__(1)

        self.assertEqual(status, HTTPStatus.BAD_REQUEST)
        self.assertFalse(session.committed)

    def test_payables_post_bad_target(self):
        session = SessionStub(
            {
                rest_assets.Account: QueryStub(first_item=None),
                rest_assets.Instrument: QueryStub(first_item=None),
            }
        )
        with self.app.test_request_context(
            "/payables",
            method="POST",
            json={
                "currency": "usd",
                "country": "us",
                "description": "Rent",
                "amount": 10.0,
                "balance": 10.0,
                "dueDate": "2026-01-01",
                "flowClass": "Expense",
                "targetAssetId": "missing",
            },
        ), patch("routes.rest_assets.current_user", self.user), patch.object(
            Config, "DB_SESSION", lambda: session, create=True
        ), patch.object(Config, "CURRENCIES", ["usd"], create=True), patch.object(
            Config, "COUNTRIES", ["US"], create=True
        ):
            response, status = rest_assets.payables.__wrapped__()

        self.assertEqual(status, HTTPStatus.BAD_REQUEST)
        self.assertEqual(session.added, [])

    def test_payables_post_success_falls_back_to_paid_with_asset_id(self):
        session = SessionStub(
            {
                rest_assets.Account: QueryStub(first_item=SimpleNamespace(id="acc-1")),
            }
        )
        with self.app.test_request_context(
            "/payables",
            method="POST",
            json={
                "currency": "usd",
                "country": "us",
                "description": "Rent",
                "amount": 10.0,
                "balance": 10.0,
                "dueDate": "2026-01-01",
                "flowClass": "Expense",
                "paidWithAssetId": "acc-1",
            },
        ), patch("routes.rest_assets.current_user", self.user), patch(
            "routes.rest_assets.reload_asset_store"
        ), patch(
            "routes.rest_assets.UserStore.get_user_config",
            return_value=SimpleNamespace(),
        ), patch.object(
            Config, "DB_SESSION", lambda: session, create=True
        ), patch.object(Config, "CURRENCIES", ["usd"], create=True), patch.object(
            Config, "COUNTRIES", ["US"], create=True
        ):
            response, status = rest_assets.payables.__wrapped__()

        self.assertEqual(status, 201)
        self.assertEqual(session.added[0].target_asset_id, "acc-1")

    def test_payables_get_put_bad_target(self):
        existing = SimpleNamespace(target_asset_id="old", flow_class="expense")
        session = SessionStub(
            {
                rest_assets.Payable: QueryStub(first_item=existing),
                rest_assets.Account: QueryStub(first_item=None),
                rest_assets.Instrument: QueryStub(first_item=None),
            }
        )
        with self.app.test_request_context(
            "/payables/1", method="PUT", json={"targetAssetId": "missing"}
        ), patch("routes.rest_assets.current_user", self.user), patch.object(
            Config, "DB_SESSION", lambda: session, create=True
        ):
            response, status = rest_assets.payables_get.__wrapped__(1)

        self.assertEqual(status, HTTPStatus.BAD_REQUEST)
        self.assertFalse(session.committed)

    def test_reload_assets(self):
        with self.app.test_request_context("/reload", method="GET"), patch(
            "routes.rest_assets.current_user", self.user
        ), patch(
            "routes.rest_assets.UserStore.get_user_config",
            return_value=SimpleNamespace(),
        ), patch(
            "routes.rest_assets.reload_asset_store"
        ) as reload_store:
            response, status = rest_assets.reload_assets.__wrapped__()

        reload_store.assert_called_once()
        self.assertEqual(status, 200)
        self.assertEqual(response.get_json(), {"message": "Assets reloaded"})


if __name__ == "__main__":
    unittest.main()
