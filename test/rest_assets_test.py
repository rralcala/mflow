import unittest
from types import SimpleNamespace
from unittest.mock import patch

from flask import Flask

import routes.rest_assets as rest_assets
import routes.rest_recurrents as rest_recurrents
from lib.config import Config
from models.models import Recurrent, RecurrentTransaction


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
                rest_assets.BondSchedule: QueryStub(
                    all_items=[row({"id": "1"}), row({"id": "2"})]
                )
            }
        )
        with self.app.test_request_context("/bondSchedules", method="GET"), patch(
            "routes.rest_assets.current_user", self.user
        ), patch.object(Config, "DB_SESSION", lambda: session, create=True):
            response, status = rest_assets.bond_schedules_all.__wrapped__()

        self.assertEqual(status, 200)
        self.assertEqual(response.headers["X-Total-Count"], "2")

    def test_bond_schedules_get_not_found(self):
        session = SessionStub({rest_assets.BondSchedule: QueryStub(first_item=None)})
        with self.app.test_request_context("/bondSchedules/1", method="GET"), patch(
            "routes.rest_assets.current_user", self.user
        ), patch.object(Config, "DB_SESSION", lambda: session, create=True):
            response, status = rest_assets.bond_schedules_get.__wrapped__("1")

        self.assertEqual(status, 404)
        self.assertEqual(response.get_json(), {"message": "Bond Schedule not found"})

    def test_bonds_all_get(self):
        session = SessionStub(
            {
                rest_assets.Bond: QueryStub(
                    all_items=[row({"id": "b"}), row({"id": "a"})]
                )
            }
        )
        with self.app.test_request_context("/bonds", method="GET"), patch(
            "routes.rest_assets.current_user", self.user
        ), patch.object(Config, "DB_SESSION", lambda: session, create=True):
            response, status = rest_assets.bonds_all.__wrapped__()

        self.assertEqual(status, 200)
        self.assertEqual(response.get_json(), [{"id": "a"}, {"id": "b"}])

    def test_bonds_get_not_found(self):
        session = SessionStub({rest_assets.Bond: QueryStub(first_item=None)})
        with self.app.test_request_context("/bonds/1", method="GET"), patch(
            "routes.rest_assets.current_user", self.user
        ), patch.object(Config, "DB_SESSION", lambda: session, create=True):
            response, status = rest_assets.bonds_get.__wrapped__("1")

        self.assertEqual(status, 404)
        self.assertEqual(response.get_json(), {"message": "Bond not found"})

    def test_deposit_certificate_schedules_all_get(self):
        session = SessionStub(
            {
                rest_assets.DepositCertificateSchedule: QueryStub(
                    all_items=[row({"id": "1"})]
                )
            }
        )
        with self.app.test_request_context(
            "/depositCertificateSchedules", method="GET"
        ), patch("routes.rest_assets.current_user", self.user), patch.object(
            Config, "DB_SESSION", lambda: session, create=True
        ):
            response, status = (
                rest_assets.deposit_certificate_schedules_all.__wrapped__()
            )

        self.assertEqual(status, 200)
        self.assertEqual(response.headers["X-Total-Count"], "1")

    def test_deposit_certificate_schedules_get_not_found(self):
        session = SessionStub(
            {rest_assets.DepositCertificateSchedule: QueryStub(first_item=None)}
        )
        with self.app.test_request_context(
            "/depositCertificateSchedules/1", method="GET"
        ), patch("routes.rest_assets.current_user", self.user), patch.object(
            Config, "DB_SESSION", lambda: session, create=True
        ):
            response, status = (
                rest_assets.deposit_certificate_schedules_get.__wrapped__("1")
            )

        self.assertEqual(status, 404)

    def test_deposit_certificates_all_get(self):
        session = SessionStub(
            {
                rest_assets.DepositCertificate: QueryStub(
                    all_items=[row({"id": "2"}), row({"id": "1"})]
                )
            }
        )
        with self.app.test_request_context("/depositCertificates", method="GET"), patch(
            "routes.rest_assets.current_user", self.user
        ), patch.object(Config, "DB_SESSION", lambda: session, create=True):
            response, status = rest_assets.deposit_certificates_all.__wrapped__()

        self.assertEqual(status, 200)
        self.assertEqual(response.get_json(), [{"id": "1"}, {"id": "2"}])

    def test_deposit_certificates_get_not_found(self):
        session = SessionStub(
            {rest_assets.DepositCertificate: QueryStub(first_item=None)}
        )
        with self.app.test_request_context(
            "/depositCertificates/1", method="GET"
        ), patch("routes.rest_assets.current_user", self.user), patch.object(
            Config, "DB_SESSION", lambda: session, create=True
        ):
            response, status = rest_assets.deposit_certificates_get.__wrapped__("1")

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
