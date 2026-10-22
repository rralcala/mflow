import io
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from test.schemas_test import api
from unittest.mock import patch

from lib.config import Config
from lib.passwords import (
    PasswordStoreError,
    hash_password,
    is_legacy_hash,
    needs_rehash,
    password_problem,
    set_password_hash,
    verify_password,
)
from lib.user_config import UserStore
from lib.util import sha256_hash
from scripts import split_user_config

NEW_PASSWORD = "a-good-new-password"


class TestHashing(unittest.TestCase):
    def test_hash_is_salted_scrypt(self):
        first, second = hash_password("pw"), hash_password("pw")
        self.assertTrue(first.startswith("scrypt:"))
        self.assertNotEqual(first, second)
        self.assertTrue(verify_password(first, "pw"))
        self.assertFalse(verify_password(first, "other"))
        self.assertFalse(needs_rehash(first))

    def test_legacy_sha256_still_verifies_and_needs_rehash(self):
        legacy = sha256_hash("pw")
        self.assertTrue(is_legacy_hash(legacy))
        self.assertTrue(verify_password(legacy, "pw"))
        self.assertFalse(verify_password(legacy, "other"))
        self.assertTrue(needs_rehash(legacy))

    def test_missing_or_malformed_hash_never_verifies(self):
        for stored in (None, "", "garbage", "pbkdf2:bogus$x$y"):
            self.assertFalse(verify_password(stored, "pw"), stored)

    def test_password_problem(self):
        self.assertIsNone(password_problem(NEW_PASSWORD))
        self.assertIn("at least", password_problem("short"))
        self.assertIn("at most", password_problem("x" * 31))
        self.assertIn("whitespace", password_problem(" " + NEW_PASSWORD))


def write_json(path: Path, data: dict, mode=0o640):
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(data))
    os.chmod(path, mode)


class DataDirTestCase(unittest.TestCase):
    """A real data dir: a main config.json listing user ids, and each user's
    login in user-<id>/config.json."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.main_file = self.base / "config.json"
        write_json(self.main_file, {"COUNTRIES": ["US"], "USERS": ["1", "2"]}, 0o440)
        write_json(
            self.user_file("1"),
            {
                "USERNAME": "jdoe",
                "NAME": "J Doe",
                "EMAIL": "jdoe@example.com",
                "PASSWORD_HASH": sha256_hash("pw-one-legacy"),
                "LAST_UNTIL": "2070-01-01",
            },
        )
        write_json(
            self.user_file("2"),
            {"USERNAME": "asmith", "PASSWORD_HASH": hash_password("pw-two-current")},
        )
        for patcher in (
            patch.object(Config, "BASE_PATH", self.base, create=True),
            patch.object(Config, "USERS", ["1", "2"], create=True),
            patch.object(
                Config,
                "SECRET_KEY",
                "unit-test-secret-key-at-least-32-bytes-long",
                create=True,
            ),
            patch.dict(UserStore.user_config, clear=True),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.main_before = self.main_file.read_text()

    def tearDown(self):
        # The API must never write the main config.
        self.assertEqual(self.main_file.read_text(), self.main_before)

    def user_file(self, user_id):
        return self.base / f"user-{user_id}" / "config.json"

    def stored_hash(self, user_id):
        return json.loads(self.user_file(user_id).read_text())["PASSWORD_HASH"]


class TestSetPasswordHash(DataDirTestCase):
    def test_updates_user_file_and_cache_keeping_other_keys(self):
        cached = UserStore.get_user_config("1")
        other_before = self.stored_hash("2")
        new_hash = hash_password(NEW_PASSWORD)
        set_password_hash("1", new_hash)

        data = json.loads(self.user_file("1").read_text())
        self.assertEqual(data["PASSWORD_HASH"], new_hash)
        self.assertEqual(data["LAST_UNTIL"], "2070-01-01")
        self.assertEqual(cached.PASSWORD_HASH, new_hash)
        self.assertEqual(stat.S_IMODE(self.user_file("1").stat().st_mode), 0o640)
        self.assertEqual(list(self.user_file("1").parent.glob(".config-*")), [])
        self.assertEqual(self.stored_hash("2"), other_before)

    def test_missing_user_file_is_a_store_error(self):
        with self.assertRaises(PasswordStoreError):
            set_password_hash("9", "x")


class TestPasswordEndpoints(DataDirTestCase):
    def setUp(self):
        super().setUp()
        self.client = api().test_client()

    def login(self, username, password):
        return self.client.post(
            "/auth/rlogin", json={"username": username, "password": password}
        )

    def change(self, current, new):
        return self.client.post(
            "/auth/password",
            json={"currentPassword": current, "newPassword": new},
        )

    def test_login_reads_user_config(self):
        response = self.login("jdoe", "pw-one-legacy")
        self.assertEqual(response.get_json(), {"id": "1", "fullName": "jdoe"})
        profile = self.client.get("/auth/profile").get_json()
        self.assertEqual(profile["name"], "J Doe")
        self.assertEqual(profile["email"], "jdoe@example.com")
        self.assertNotIn("PASSWORD_HASH", profile["config"])
        self.assertNotIn("USERNAME", profile["config"])

    def test_unlisted_user_dir_cannot_log_in(self):
        write_json(
            self.user_file("3"),
            {"USERNAME": "ghost", "PASSWORD_HASH": hash_password("pw-ghost-pass")},
        )
        self.assertEqual(self.login("ghost", "pw-ghost-pass").status_code, 401)

    def test_login_upgrades_legacy_hash(self):
        self.assertEqual(self.login("jdoe", "pw-one-legacy").status_code, 200)
        stored = self.stored_hash("1")
        self.assertTrue(stored.startswith("scrypt:"))
        self.assertTrue(verify_password(stored, "pw-one-legacy"))
        self.client.get("/auth/rlogout")
        self.assertEqual(self.login("jdoe", "pw-one-legacy").status_code, 200)

    def test_failed_login_leaves_legacy_hash(self):
        self.assertEqual(self.login("jdoe", "wrong").status_code, 401)
        self.assertEqual(self.stored_hash("1"), sha256_hash("pw-one-legacy"))

    def test_change_requires_login(self):
        self.assertEqual(self.change("pw-two-current", NEW_PASSWORD).status_code, 401)

    def test_change_requires_current_password(self):
        before = self.stored_hash("2")
        self.login("asmith", "pw-two-current")
        self.assertEqual(self.change("wrong", NEW_PASSWORD).status_code, 403)
        self.assertEqual(self.stored_hash("2"), before)

    def test_change_rejects_weak_or_same_password(self):
        self.login("asmith", "pw-two-current")
        self.assertEqual(self.change("pw-two-current", "short").status_code, 400)
        response = self.change("pw-two-current", "pw-two-current")
        self.assertEqual(response.status_code, 400)

    def test_change_only_affects_caller(self):
        other_before = self.stored_hash("1")
        self.login("asmith", "pw-two-current")
        self.assertEqual(self.change("pw-two-current", NEW_PASSWORD).status_code, 200)
        self.assertEqual(self.stored_hash("1"), other_before)

        self.client.get("/auth/rlogout")
        self.assertEqual(self.login("asmith", "pw-two-current").status_code, 401)
        self.assertEqual(self.login("asmith", NEW_PASSWORD).status_code, 200)

    def test_change_with_bearer_token(self):
        self.login("asmith", "pw-two-current")
        token = self.client.get("/auth/jwt").get_data(as_text=True)
        client = api().test_client()  # no session cookie
        response = client.post(
            "/auth/password",
            json={"currentPassword": "pw-two-current", "newPassword": NEW_PASSWORD},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)

    def test_unwritable_store_is_reported(self):
        self.login("asmith", "pw-two-current")
        with patch(
            "routes.auth.set_password_hash",
            side_effect=PasswordStoreError("read-only"),
        ):
            response = self.change("pw-two-current", NEW_PASSWORD)
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("read-only", response.get_data(as_text=True))


class TestSplitUserConfig(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.main_file = self.base / "config.json"
        write_json(
            self.main_file,
            {
                "SECRET_KEY": "s",
                "USERS": {
                    "1": {"username": "jdoe", "name": "J", "password": "h1"},
                    "2": {"username": "asmith", "password": "h2"},
                },
            },
        )
        write_json(self.base / "user-1" / "config.json", {"LAST_UNTIL": "2070"})

    def run_script(self):
        with patch.object(
            sys, "argv", ["split_user_config", "--base", str(self.base)]
        ), patch("sys.stdout", io.StringIO()):
            split_user_config.main()

    def read(self, path):
        return json.loads(path.read_text())

    def test_moves_logins_and_leaves_ids(self):
        self.run_script()
        self.assertEqual(
            self.read(self.main_file), {"SECRET_KEY": "s", "USERS": ["1", "2"]}
        )
        self.assertEqual(
            self.read(self.base / "user-1" / "config.json"),
            {
                "LAST_UNTIL": "2070",
                "USERNAME": "jdoe",
                "NAME": "J",
                "PASSWORD_HASH": "h1",
            },
        )
        new_file = self.base / "user-2" / "config.json"
        self.assertEqual(
            self.read(new_file), {"USERNAME": "asmith", "PASSWORD_HASH": "h2"}
        )
        self.assertEqual(stat.S_IMODE(new_file.stat().st_mode), 0o600)
        backup = self.read(self.base / "config.json.pre-split.bak")
        self.assertIn("password", backup["USERS"]["1"])

        self.run_script()  # already split: a no-op
        self.assertEqual(self.read(self.main_file)["USERS"], ["1", "2"])

    def test_conflict_writes_nothing(self):
        write_json(self.base / "user-1" / "config.json", {"USERNAME": "other"})
        before = self.main_file.read_text()
        with self.assertRaises(SystemExit):
            self.run_script()
        self.assertEqual(self.main_file.read_text(), before)
        self.assertFalse((self.base / "user-2").exists())


if __name__ == "__main__":
    unittest.main()
