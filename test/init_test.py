import json
import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import routes.auth  # noqa: F401  registers login_manager's loaders, as service.py does
from init import create_app, initialize_app, login_manager, parse_args
from lib.config import Config


class TestParseArgs(unittest.TestCase):
    def test_debug_off_by_default(self):
        args = parse_args(["--base", "/data/"])
        self.assertEqual(args.base, "/data/")
        self.assertFalse(args.debug)

    def test_debug_flag(self):
        self.assertTrue(parse_args(["--base", "/data/", "--debug"]).debug)


class TestCreateApp(unittest.TestCase):
    def setUp(self):
        patcher = patch.object(Config, "SECRET_KEY", "secret", create=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_docs_disabled_without_debug(self):
        client = create_app(debug=False).test_client()
        self.assertEqual(client.get("/openapi.json").status_code, 404)
        self.assertEqual(client.get("/docs").status_code, 404)

    def test_docs_enabled_with_debug(self):
        client = create_app(debug=True).test_client()
        self.assertEqual(client.get("/openapi.json").status_code, 200)
        self.assertEqual(client.get("/docs").status_code, 200)

    def test_cookie_security_scheme_documented(self):
        spec = create_app(debug=True).test_client().get("/openapi.json").get_json()
        cookie = spec["components"]["securitySchemes"]["CookieAuth"]
        self.assertEqual((cookie["in"], cookie["name"]), ("cookie", "session"))

    def test_login_manager_attached(self):
        app = create_app()
        self.assertIs(app.login_manager, login_manager)
        self.assertEqual(app.secret_key, "secret")


class TestInitializeApp(unittest.TestCase):
    def setUp(self):
        # Patched so the shared Config class is restored afterwards.
        for name in ("BASE_PATH", "DB_SESSION", "SECRET_KEY", "COUNTRIES"):
            patcher = patch.object(Config, name, None, create=True)
            patcher.start()
            self.addCleanup(patcher.stop)
        # Keep the root logger's level untouched for the rest of the suite.
        patcher = patch("init.config_logging", return_value=logging.getLogger())
        patcher.start()
        self.addCleanup(patcher.stop)

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        (self.base / "mydatabase.db").touch()
        (self.base / "config.json").write_text(
            json.dumps({"SECRET_KEY": "secret", "COUNTRIES": []})
        )

    def test_debug_flag_enables_docs(self):
        app = initialize_app(["--base", str(self.base), "--debug"])
        self.assertTrue(app.enable_openapi)
        self.assertEqual(app.test_client().get("/openapi.json").status_code, 200)

    def test_no_debug_flag_disables_docs(self):
        app = initialize_app(["--base", str(self.base)])
        self.assertFalse(app.enable_openapi)
        self.assertEqual(app.test_client().get("/openapi.json").status_code, 404)

    def test_missing_database_exits(self):
        (self.base / "mydatabase.db").unlink()
        with self.assertRaises(SystemExit):
            initialize_app(["--base", str(self.base)])


if __name__ == "__main__":
    unittest.main()
