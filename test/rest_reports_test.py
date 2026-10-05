import unittest
from types import SimpleNamespace
from unittest.mock import patch

from flask import Flask

import routes.rest_reports as rest_reports


class TestRestReportsRoutes(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.user = SimpleNamespace(id="1")

    def test_future_timeline_defaults_to_last_until(self):
        data = {"months": [{"id": "2030-01"}, {"id": "2030-02"}], "summary": {}}
        user_config = SimpleNamespace(
            LAST_UNTIL="2075-08-01",
            INFLATION_RATES={"PY": 0.04},
            DESIRED_ESTATE=850000.0,
        )

        with self.app.test_request_context(
            "/future_timeline?capitalGrowth=1", method="GET"
        ), patch("routes.rest_reports.current_user", self.user), patch(
            "routes.rest_reports.UserStore.get_user_config",
            return_value=user_config,
        ), patch(
            "routes.rest_reports.get_asset_store", return_value={"USD": []}
        ), patch(
            "routes.rest_reports.vft.future_timeline", return_value=data
        ) as timeline_mock:
            response, status = rest_reports.future_timeline.__wrapped__()

        self.assertEqual(status, 200)
        self.assertEqual(response.headers["X-Total-Count"], "2")
        self.assertEqual(response.get_json(), data)
        kwargs = timeline_mock.call_args.kwargs
        self.assertEqual(kwargs["end_date"], "2075-08-01")
        self.assertEqual(kwargs["inflation_rates"], {"PY": 0.04})
        self.assertTrue(kwargs["include_capital_growth"])
        self.assertEqual(kwargs["desired_estate"], 850000.0)

    def test_future_timeline_end_date_override(self):
        with self.app.test_request_context(
            "/future_timeline?endDate=2040-01-01", method="GET"
        ), patch("routes.rest_reports.current_user", self.user), patch(
            "routes.rest_reports.UserStore.get_user_config",
            return_value=SimpleNamespace(LAST_UNTIL="2075-08-01"),
        ), patch(
            "routes.rest_reports.get_asset_store", return_value={"USD": []}
        ), patch(
            "routes.rest_reports.vft.future_timeline", return_value={"months": []}
        ) as timeline_mock:
            rest_reports.future_timeline.__wrapped__()

        self.assertEqual(timeline_mock.call_args.kwargs["end_date"], "2040-01-01")
        self.assertFalse(timeline_mock.call_args.kwargs["include_capital_growth"])

    def test_future_timeline_bad_request(self):
        with self.app.test_request_context(
            "/future_timeline?endDate=2000-01-01", method="GET"
        ), patch("routes.rest_reports.current_user", self.user), patch(
            "routes.rest_reports.UserStore.get_user_config",
            return_value=SimpleNamespace(LAST_UNTIL="2075-08-01"),
        ), patch(
            "routes.rest_reports.get_asset_store", return_value={"USD": []}
        ), patch(
            "routes.rest_reports.vft.future_timeline",
            side_effect=ValueError("endDate must not be before startDate"),
        ):
            response, status = rest_reports.future_timeline.__wrapped__()

        self.assertEqual(status, 400)
        self.assertEqual(
            response.get_json(), {"message": "endDate must not be before startDate"}
        )


if __name__ == "__main__":
    unittest.main()
