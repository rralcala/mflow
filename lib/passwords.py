import hmac
import json
import threading
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash

from lib.config import Config, write_json_atomic
from lib.user_config import UserStore, user_config_path
from lib.util import sha256_hash

# scrypt: salted and memory-hard. Stored as "scrypt:<params>$<salt>$<hash>".
HASH_METHOD = "scrypt"
MIN_PASSWORD_LENGTH = 12
# Login rejects anything longer, so a new password can't exceed it either.
MAX_PASSWORD_LENGTH = 30

_write_lock = threading.Lock()


class PasswordStoreError(Exception):
    """A user's config.json could not be read or written."""


def hash_password(password: str) -> str:
    return generate_password_hash(password, method=HASH_METHOD)


def is_legacy_hash(stored: str) -> bool:
    """Unsalted SHA-256 hex digests, from before the move to scrypt."""
    return (
        len(stored) == 64
        and "$" not in stored
        and all(c in "0123456789abcdef" for c in stored.lower())
    )


def verify_password(stored: str | None, password: str) -> bool:
    if not stored:
        return False
    if is_legacy_hash(stored):
        return hmac.compare_digest(stored.lower(), sha256_hash(password))
    try:
        return check_password_hash(stored, password)
    except ValueError:  # unknown or malformed hash format
        return False


def needs_rehash(stored: str) -> bool:
    return not stored.startswith(HASH_METHOD + ":")


def password_problem(password: str) -> str | None:
    """Why `password` can't be used as a new password, or None if it can."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    if len(password) > MAX_PASSWORD_LENGTH:
        return f"Password must be at most {MAX_PASSWORD_LENGTH} characters."
    if password.strip() != password:
        return "Password can't start or end with whitespace."
    return None


def set_password_hash(user_id: str, password_hash: str, base: Path | None = None):
    """Store a new password hash in the user's own user-<id>/config.json.

    The main config.json is never written. The file is re-read rather than
    rebuilt from UserConfig, so keys this process doesn't know about survive,
    and a cached UserConfig is updated to match.
    """
    if base is None and getattr(Config, "BASE_PATH", None) is None:
        raise PasswordStoreError("No data directory configured")
    path = user_config_path(user_id, base)
    with _write_lock:
        try:
            data = json.loads(path.read_text())
            if not isinstance(data, dict):
                raise PasswordStoreError(f"{path} is not a JSON object")
            data["PASSWORD_HASH"] = password_hash
            write_json_atomic(path, data)
        except (OSError, json.JSONDecodeError) as e:
            raise PasswordStoreError(f"Can't update {path}: {e}") from e
    cached = UserStore.user_config.get(user_id)
    if cached is not None:
        cached.PASSWORD_HASH = password_hash
