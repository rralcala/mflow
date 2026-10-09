import unittest
from test.rest_assets_test import QueryStub, SessionStub, row
from types import SimpleNamespace
from unittest.mock import patch

from apiflask import HTTPError
from flask import Flask

from lib.config import Config
from lib.util import paginate
from models.models import Recurrent
from routes.assets import rest_assets, rest_certificates, rest_recurrents


class TestPaginate(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.items = list(range(10))

    def run_paginate(self, query, items=None):
        with self.app.test_request_context(f"/x{query}"):
            return paginate(self.items if items is None else items)

    def test_no_params_returns_everything(self):
        self.assertEqual(self.run_paginate(""), self.items)

    def test_start_and_end(self):
        self.assertEqual(self.run_paginate("?_start=2&_end=5"), [2, 3, 4])

    def test_only_start_or_only_end(self):
        self.assertEqual(self.run_paginate("?_start=8"), [8, 9])
        self.assertEqual(self.run_paginate("?_end=2"), [0, 1])

    def test_range_past_the_end(self):
        self.assertEqual(self.run_paginate("?_start=8&_end=50"), [8, 9])
        self.assertEqual(self.run_paginate("?_start=20&_end=30"), [])

    def test_invalid_values_are_bad_requests(self):
        for query in ("?_start=a&_end=2", "?_start=0&_end=b", "?_start=-1&_end=2"):
            with self.assertRaises(HTTPError) as ctx:
                self.run_paginate(query)
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertIn("_start", ctx.exception.message)

    def test_non_list_payload_untouched(self):
        payload = {"a": 1}
        self.assertEqual(self.run_paginate("?_start=0&_end=1", payload), payload)


class TestEndpointTotals(unittest.TestCase):
    """X-Total-Count must stay the unsliced total when a range is requested."""

    def setUp(self):
        self.app = Flask(__name__)
        self.user = SimpleNamespace(id="1")

    def test_bond_schedules(self):
        session = SessionStub(
            {
                rest_certificates.BondSchedule: QueryStub(
                    all_items=[row({"id": str(i)}) for i in range(5)]
                )
            }
        )
        with self.app.test_request_context(
            "/bondSchedules?_start=1&_end=3", method="GET"
        ), patch("routes.rest_certificates.current_user", self.user), patch.object(
            Config, "DB_SESSION", lambda: session, create=True
        ):
            response, status = rest_certificates.bond_schedules_all.__wrapped__()

        self.assertEqual(status, 200)
        self.assertEqual(response.get_json(), [{"id": "1"}, {"id": "2"}])
        self.assertEqual(response.headers["X-Total-Count"], "5")

    def test_recurrents(self):
        session = SessionStub(
            {
                Recurrent: QueryStub(
                    all_items=[row({"id": c}) for c in "dcba"],
                )
            }
        )
        with self.app.test_request_context(
            "/recurrents?_start=0&_end=2", method="GET"
        ), patch("routes.rest_recurrents.current_user", self.user), patch.object(
            Config, "DB_SESSION", lambda: session, create=True
        ):
            response, status = rest_recurrents.recurrents_all.__wrapped__()

        self.assertEqual(response.get_json(), [{"id": "a"}, {"id": "b"}])
        self.assertEqual(response.headers["X-Total-Count"], "4")

    def test_monthly_transactions(self):
        txs = [{"id": str(i), "amount": -1.0} for i in range(4)]
        with self.app.test_request_context(
            "/monthlyTransactions?_start=3&_end=10", method="GET"
        ), patch("routes.rest_assets.current_user", self.user), patch(
            "routes.rest_assets.load_tx", return_value=txs
        ):
            response = rest_assets.monthly_transactions.__wrapped__()

        self.assertEqual(response.get_json(), [txs[3]])
        self.assertEqual(response.headers["X-Total-Count"], "4")


if __name__ == "__main__":
    unittest.main()
