import unittest
from types import SimpleNamespace
from unittest.mock import patch

from flask import Flask

import routes.rest_reports as rest_reports


class TestRestReportsRoutes(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.user = SimpleNamespace(id="1")

    def test_future_timeline_success_and_pagination(self):
        data = [
            {"id": "r1", "date": "2030-01-01"},
            {"id": "r2", "date": "2030-02-01"},
            {"id": "r3", "date": "2030-03-01"},
        ]

        with self.app.test_request_context(
            "/future_timeline?mode=flat&granularity=yearly&startDate=2030-01-01&endDate=2030-12-31&_start=1&_end=3",
            method="GET",
        ), patch("routes.rest_reports.current_user", self.user), patch(
            "routes.rest_reports.UserStore.get_user_config",
            return_value=SimpleNamespace(),
        ), patch(
            "routes.rest_reports.get_asset_store", return_value={"USD": []}
        ), patch(
            "routes.rest_reports.vft.future_timeline", return_value=data
        ) as timeline_mock:
            response, status = rest_reports.future_timeline.__wrapped__()

        self.assertEqual(status, 200)
        self.assertEqual(response.headers["X-Total-Count"], "3")
        self.assertEqual(response.get_json(), data[1:3])
        self.assertEqual(timeline_mock.call_args.kwargs["mode"], "flat")
        self.assertEqual(timeline_mock.call_args.kwargs["granularity"], "yearly")

    def test_future_timeline_bad_request(self):
        with self.app.test_request_context(
            "/future_timeline?mode=bad", method="GET"
        ), patch("routes.rest_reports.current_user", self.user), patch(
            "routes.rest_reports.UserStore.get_user_config",
            return_value=SimpleNamespace(),
        ), patch(
            "routes.rest_reports.get_asset_store", return_value={"USD": []}
        ), patch(
            "routes.rest_reports.vft.future_timeline",
            side_effect=ValueError("invalid mode"),
        ):
            response, status = rest_reports.future_timeline.__wrapped__()

        self.assertEqual(status, 400)
        self.assertEqual(response.get_json(), {"message": "invalid mode"})


if __name__ == "__main__":
    unittest.main()
