"""json-server `_sort` / `_order` on list endpoints."""

import unittest
from test.rest_assets_test import QueryStub, SessionStub, api_app, row, run_view
from types import SimpleNamespace
from unittest.mock import patch

from apiflask import HTTPError
from flask import Flask

import routes.rest_reports as rest_reports
from lib.config import Config
from lib.util import sort_items
from models.bond import Bond, BondSchedule
from models.deposit_certificate import DepositCertificateSchedule
from models.models import Recurrent, RecurrentTransaction
from routes.assets import rest_assets, rest_certificates, rest_recurrents
from routes.schemas import ExchangeRateOut, RecurrentTransactionOut


class TestSortItems(unittest.TestCase):
    def sort(self, items, query, **kw):
        with Flask(__name__).test_request_context("/"):
            return sort_items(items, query, ExchangeRateOut, **kw)

    def ids(self, items):
        return [item["id"] for item in items]

    def setUp(self):
        self.items = [
            {"id": "b", "rate": 2.0},
            {"id": "C", "rate": None},
            {"id": "a", "rate": 3.0},
            {"id": "d"},
        ]

    def test_no_sort_and_no_default_keeps_order(self):
        self.assertEqual(self.sort(self.items, {}), self.items)

    def test_strings_compare_case_insensitively(self):
        self.assertEqual(self.ids(self.sort(self.items, {"sort": "id"})), list("abCd"))

    def test_order_is_case_insensitive(self):
        for order in ("DESC", "desc", "Desc"):
            result = self.sort(self.items, {"sort": "id", "order": order})
            self.assertEqual(self.ids(result), list("dCba"), order)

    def test_missing_and_none_values_go_last_in_both_directions(self):
        asc = self.sort(self.items, {"sort": "rate"})
        desc = self.sort(self.items, {"sort": "rate", "order": "DESC"})
        self.assertEqual(self.ids(asc), ["b", "a", "C", "d"])
        self.assertEqual(self.ids(desc), ["a", "b", "C", "d"])

    def test_mixed_types_do_not_raise(self):
        items = [{"id": "x", "rate": "n/a"}, {"id": "y", "rate": 1.5}, {"id": "z"}]
        self.assertEqual(self.ids(self.sort(items, {"sort": "rate"})), list("yxz"))

    def test_equal_values_keep_their_order(self):
        items = [{"id": "x", "rate": 1}, {"id": "y", "rate": 1}]
        for order in ("ASC", "DESC"):
            result = self.sort(items, {"sort": "rate", "order": order})
            self.assertEqual(self.ids(result), ["x", "y"])

    def test_default_applies_only_without_sort(self):
        result = self.sort(self.items, {}, default="rate", default_order="DESC")
        self.assertEqual(self.ids(result), ["a", "b", "C", "d"])
        # An explicit _sort without _order is ascending, not the default order.
        result = self.sort(self.items, {"sort": "id"}, default_order="DESC")
        self.assertEqual(self.ids(result), list("abCd"))

    def test_unknown_key_is_a_bad_request(self):
        with self.assertRaises(HTTPError) as ctx:
            self.sort(self.items, {"sort": "nope"})
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(
            ctx.exception.message,
            "Can't sort by 'nope'; expected one of id, rate, weekChange",
        )

    def test_unknown_order_is_a_bad_request(self):
        with self.assertRaises(HTTPError) as ctx:
            self.sort(self.items, {"sort": "id", "order": "sideways"})
        self.assertEqual(ctx.exception.status_code, 400)

    def test_accepts_schema_instances_and_data_keys(self):
        items = [{"id": 1, "transactionDate": "2026-02-01"}, {"id": 2}]
        with Flask(__name__).test_request_context("/"):
            result = sort_items(
                items,
                {"sort": "transactionDate", "order": "DESC"},
                RecurrentTransactionOut(),
            )
        self.assertEqual([i["id"] for i in result], [1, 2])


class TestListEndpointsSort(unittest.TestCase):
    def setUp(self):
        self.app = api_app()
        user = SimpleNamespace(id="1")
        for target in (
            patch.object(rest_assets, "current_user", user),
            patch.object(rest_certificates, "current_user", user),
            patch.object(rest_recurrents, "current_user", user),
            patch.object(rest_reports, "current_user", user),
        ):
            target.start()
            self.addCleanup(target.stop)

    def get(self, view, query, models):
        session = SessionStub(
            {model: QueryStub(all_items=items) for model, items in models.items()}
        )
        with self.app.test_request_context(f"/x{query}"), patch.object(
            Config, "DB_SESSION", lambda: session, create=True
        ):
            response, status = run_view(view)
        return response, status

    def ids(self, response):
        return [item["id"] for item in response.get_json()]

    def test_bonds_sort_by_any_field(self):
        bonds = [
            row({"id": 1, "name": "B", "rate": 0.05, "capital": 10}),
            row({"id": 2, "name": "A", "rate": 0.07, "capital": 30}),
            row({"id": 3, "name": "C", "rate": 0.06, "capital": 20}),
        ]
        cases = {
            "": [2, 1, 3],  # default: name
            "?_sort=rate&_order=DESC": [2, 3, 1],
            "?_sort=capital&_order=asc": [1, 3, 2],
            "?_sort=id&_order=DESC": [3, 2, 1],
        }
        for query, expected in cases.items():
            response, status = self.get(
                rest_certificates.bonds_list, query, {Bond: bonds}
            )
            self.assertEqual(status, 200, query)
            self.assertEqual(self.ids(response), expected, query)

    def test_unknown_sort_key_is_400(self):
        response, status = self.get(
            rest_certificates.bonds_list, "?_sort=bogus", {Bond: []}
        )
        self.assertEqual(status, 400)
        self.assertIn("Can't sort by 'bogus'", response.get_json()["message"])

    def test_sort_happens_before_pagination(self):
        bonds = [row({"id": i, "name": n}) for i, n in enumerate("dcba")]
        response, status = self.get(
            rest_certificates.bonds_list,
            "?_sort=name&_order=ASC&_start=0&_end=2",
            {Bond: bonds},
        )
        self.assertEqual(self.ids(response), [3, 2])
        self.assertEqual(response.headers["X-Total-Count"], "4")

    def test_schedules_sort(self):
        schedules = [
            row({"id": 1, "transactionDate": "2027-01-01", "amount": 5.0}),
            row({"id": 2, "transactionDate": "2026-01-01", "amount": 9.0}),
        ]
        for view, model in (
            (rest_certificates.bond_schedules_list, BondSchedule),
            (
                rest_certificates.deposit_certificate_schedules_list,
                DepositCertificateSchedule,
            ),
        ):
            response, _ = self.get(view, "", {model: schedules})
            self.assertEqual(self.ids(response), [2, 1])  # default: date
            response, _ = self.get(
                view, "?_sort=amount&_order=DESC", {model: schedules}
            )
            self.assertEqual(self.ids(response), [2, 1])
            response, _ = self.get(view, "?_sort=id", {model: schedules})
            self.assertEqual(self.ids(response), [1, 2])

    def test_recurrents_sort(self):
        recurrents = [
            row({"id": "b", "amount": -10.0}),
            row({"id": "a", "amount": -50.0}),
        ]
        response, _ = self.get(
            rest_recurrents.recurrents_list, "", {Recurrent: recurrents}
        )
        self.assertEqual(self.ids(response), ["a", "b"])
        response, _ = self.get(
            rest_recurrents.recurrents_list,
            "?_sort=amount&_order=DESC",
            {Recurrent: recurrents},
        )
        self.assertEqual(self.ids(response), ["b", "a"])

    def test_recurrent_transactions_default_newest_first(self):
        def tx(id, date, amount):
            return SimpleNamespace(
                parent_id="Food",
                to_dict=lambda: {
                    "id": id,
                    "transactionDate": date,
                    "amount": amount,
                },
            )

        models = {
            Recurrent: [],
            RecurrentTransaction: [
                tx(1, "2026-01-01", -5.0),
                tx(2, "2026-03-01", -1.0),
                tx(3, "2026-02-01", -9.0),
            ],
        }
        view = rest_recurrents.recurrent_transactions_list
        self.assertEqual(self.ids(self.get(view, "", models)[0]), [2, 3, 1])
        self.assertEqual(
            self.ids(self.get(view, "?_sort=amount&_order=ASC", models)[0]),
            [3, 1, 2],
        )

    def test_monthly_transactions_sort(self):
        txs = [
            {"id": "x", "assetId": "a", "amount": -1.0, "yearMonth": "2026-12"},
            {"id": "y", "assetId": "b", "amount": -3.0, "yearMonth": "2026-11"},
        ]
        with patch.object(rest_assets, "load_tx", return_value=txs):
            response, _ = self.get(
                rest_assets.monthly_transactions, "?_sort=yearMonth", {}
            )
            self.assertEqual(self.ids(response), ["y", "x"])
            response, _ = self.get(
                rest_assets.monthly_transactions, "?_sort=amount&_order=DESC", {}
            )
            self.assertEqual(self.ids(response), ["x", "y"])

    def test_exchange_rates_sort_and_paginate(self):
        rates = {"USDPYG": 7000.0, "BTCUSD": 90000.0, "GLD": 300.0}
        config = SimpleNamespace(SECONDARY_CURRENCY="PYG")
        with patch.object(
            rest_reports.UserStore, "get_user_config", return_value=config
        ), patch.object(Config, "TRADED_CRYPTO", ["BTC"], create=True), patch.object(
            Config, "TRADED_STOCKS", [], create=True
        ), patch.object(
            Config, "TRADED_METALS", ["GLD"], create=True
        ), patch.object(
            rest_reports.ExchangeRates, "get_all", return_value=rates
        ), patch.object(
            rest_reports.ExchangeRates, "local_quotes_on", return_value=[]
        ):
            response, _ = self.get(rest_reports.exchange_rates, "", {})
            self.assertEqual(self.ids(response), ["BTCUSD", "GLD", "USDPYG"])
            response, _ = self.get(
                rest_reports.exchange_rates, "?_sort=rate&_order=DESC&_end=2", {}
            )
            self.assertEqual(self.ids(response), ["BTCUSD", "USDPYG"])
            self.assertEqual(response.headers["X-Total-Count"], "3")

    def test_upcoming_payments_default_and_explicit_sort(self):
        payments = [
            {"id": "p1", "date": "2026-12-05", "country": "US", "amount": 1.0},
            {"id": "p2", "date": "2026-12-01", "country": "UY", "amount": 3.0},
            {"id": "p3", "date": "2026-12-09", "country": "PY", "amount": 2.0},
        ]
        with patch.object(rest_reports.UserStore, "get_user_config"), patch.object(
            rest_reports, "get_asset_store"
        ), patch.object(
            rest_reports.vup,
            "upcoming_payments_flat",
            side_effect=lambda *_: [dict(p) for p in payments],
        ):
            response, _ = self.get(rest_reports.upcoming_payments_flat, "", {})
            # Default: month, then country (PY, US, UY), then date.
            self.assertEqual(self.ids(response), ["p3", "p1", "p2"])
            response, _ = self.get(
                rest_reports.upcoming_payments_flat, "?_sort=date&_order=ASC", {}
            )
            self.assertEqual(self.ids(response), ["p2", "p1", "p3"])
            response, _ = self.get(
                rest_reports.upcoming_payments_flat, "?_sort=amount&_order=DESC", {}
            )
            self.assertEqual(self.ids(response), ["p2", "p3", "p1"])


if __name__ == "__main__":
    unittest.main()
