import unittest

import jwt
from apiflask import APIFlask
from flask_login import LoginManager, login_user

from lib.config import Config
from models.models import User
from routes.auth import ALGORITHM, load_user_from_request
from routes.security import auth


class TestDualAuth(unittest.TestCase):
    def setUp(self):
        Config.SECRET_KEY = "unit-test-secret"
        Config.USERS = {"1": {"username": "u", "name": "u", "password": "x"}}
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
        token = jwt.encode({"sub": "1"}, Config.SECRET_KEY, algorithm=ALGORITHM)
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


if __name__ == "__main__":
    unittest.main()
