import unittest
from types import SimpleNamespace
from unittest.mock import patch

from flask import Flask

import routes.auth as auth_routes
from lib.user_config import MASK, UserConfig


class TestUserConfigPublicDict(unittest.TestCase):
    def setUp(self):
        self.user_config = UserConfig("1")
        self.user_config.COINBASE_API_KEY = "real-key"
        self.user_config.COINBASE_API_SECRET = "real-secret"
        self.user_config.CRYPTO_RATES = {"USDC": "0.035"}
        self.user_config.ASSETS = {"USD": ["cached asset"]}

    def test_masks_credentials(self):
        public = self.user_config.to_public_dict()

        self.assertEqual(public["COINBASE_API_KEY"], MASK)
        self.assertEqual(public["COINBASE_API_SECRET"], MASK)
        self.assertNotIn("real-key", str(public))
        self.assertNotIn("real-secret", str(public))

    def test_unset_credentials_stay_empty(self):
        self.user_config.COINBASE_API_SECRET = ""

        self.assertEqual(self.user_config.to_public_dict()["COINBASE_API_SECRET"], "")

    def test_omits_asset_cache(self):
        self.assertNotIn("ASSETS", self.user_config.to_public_dict())

    def test_keeps_settings(self):
        public = self.user_config.to_public_dict()

        self.assertEqual(public["USER_ID"], "1")
        self.assertEqual(public["LAST_UNTIL"], "2075-01-01")
        self.assertEqual(public["CRYPTO_RATES"], {"USDC": "0.035"})
        self.assertEqual(public["INFLATION_RATES"]["PY"], 0.035)
        self.assertEqual(list(public), sorted(public))


class TestProfileRoute(unittest.TestCase):
    def test_profile(self):
        user = SimpleNamespace(
            id="1", username="jdoe", name="J Doe", email="jdoe@example.com"
        )
        user_config = UserConfig("1")
        user_config.COINBASE_API_SECRET = "real-secret"

        with Flask(__name__).test_request_context("/profile"), patch(
            "routes.auth.current_user", user
        ), patch(
            "routes.auth.UserStore.get_user_config", return_value=user_config
        ) as get_config:
            response, status = auth_routes.profile.__wrapped__()

        self.assertEqual(status, 200)
        get_config.assert_called_once_with("1")
        body = response.get_json()
        self.assertEqual(body["username"], "jdoe")
        self.assertEqual(body["name"], "J Doe")
        self.assertEqual(body["email"], "jdoe@example.com")
        self.assertEqual(body["config"]["COINBASE_API_SECRET"], MASK)
        self.assertNotIn("password", body)


if __name__ == "__main__":
    unittest.main()
