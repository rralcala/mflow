import unittest
from unittest.mock import patch

import jwt
from apiflask import APIFlask
from flask_login import LoginManager, login_user

from lib.config import Config
from lib.user_config import UserConfig, UserStore
from models.models import User
from routes.auth import load_user_from_request
from routes.security import add_cookie_security, auth, security_schemes


class TestDualAuth(unittest.TestCase):
    def setUp(self):
        # Patched (not assigned) so the shared Config class is restored afterwards.
        for name, value in {
            "SECRET_KEY": "unit-test-secret-key-at-least-32-bytes-long",
            "USERS": ["1"],
        }.items():
            patcher = patch.object(Config, name, value, create=True)
            patcher.start()
            self.addCleanup(patcher.stop)
        # The login normally loaded from user-1/config.json.
        user_config = UserConfig("1")
        user_config.USERNAME = "u"
        patcher = patch.dict(UserStore.user_config, {"1": user_config}, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.app = APIFlask(__name__)
        self.app.secret_key = Config.SECRET_KEY
        lm = LoginManager(self.app)
        lm.user_loader(
            lambda uid: User(uid, "u", "u", "x", "e") if uid == "1" else None
        )
        lm.request_loader(load_user_from_request)

        @self.app.get("/login")
        def login():
            login_user(User("1", "u", "u", "x", "e"))
            return "ok"

        @self.app.get("/protected")
        @self.app.auth_required(auth)
        def protected():
            return {"user": auth.current_user.id}

        self.client = self.app.test_client()

    def test_unauthenticated(self):
        response = self.client.get("/protected")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json(), {"message": "Unauthorized"})

    def test_cookie(self):
        self.client.get("/login")
        response = self.client.get("/protected")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"user": "1"})

    def test_bearer_token(self):
        token = jwt.encode(
            {"sub": "1"}, Config.SECRET_KEY, algorithm=Config.SECRET_ALGORITHM
        )
        response = self.client.get(
            "/protected", headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"user": "1"})

    def test_invalid_bearer_token(self):
        response = self.client.get(
            "/protected", headers={"Authorization": "Bearer garbage"}
        )
        self.assertEqual(response.status_code, 401)


class TestCookieSecurityScheme(unittest.TestCase):
    def setUp(self):
        self.app = APIFlask(__name__)
        self.app.config["SECURITY_SCHEMES"] = security_schemes("session")
        self.app.spec_processor(add_cookie_security)

        @self.app.get("/protected")
        @self.app.auth_required(auth)
        def protected():
            return {}

        @self.app.get("/public")
        def public():
            return {}

        self.spec = self.app.spec

    def test_cookie_scheme_declared(self):
        schemes = self.spec["components"]["securitySchemes"]
        self.assertEqual(schemes["BearerAuth"]["scheme"], "bearer")
        cookie = schemes["CookieAuth"]
        self.assertEqual(
            (cookie["type"], cookie["in"], cookie["name"]),
            ("apiKey", "cookie", "session"),
        )

    def test_protected_operation_accepts_either_scheme(self):
        self.assertEqual(
            self.spec["paths"]["/protected"]["get"]["security"],
            [{"BearerAuth": []}, {"CookieAuth": []}],
        )

    def test_public_operation_has_no_security(self):
        self.assertNotIn("security", self.spec["paths"]["/public"]["get"])

    def test_processor_is_idempotent(self):
        spec = {"paths": {"/p": {"get": {"security": [{"BearerAuth": []}]}}}}
        add_cookie_security(add_cookie_security(spec))
        self.assertEqual(
            spec["paths"]["/p"]["get"]["security"],
            [{"BearerAuth": []}, {"CookieAuth": []}],
        )


if __name__ == "__main__":
    unittest.main()
