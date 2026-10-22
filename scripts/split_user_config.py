"""
Moves each user's login (username, name, email, password hash) out of the main
config.json and into their own user-<id>/config.json, leaving only the list of
user ids in the main file's USERS. The API never writes the main config.json;
this offline script is the only thing that does.

Safe to re-run: a main config whose USERS is already a list is left alone.
Nothing is written if a user's file already holds a different value for a key
being moved. The old main config is kept as config.json.pre-split.bak.

Usage:
    python -m scripts.split_user_config --base /path/to/base-dir
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

from lib.config import write_json_atomic
from lib.user_config import user_config_path

# Old key in the main config's USERS entry -> key in user-<id>/config.json.
MOVED_KEYS = {
    "username": "USERNAME",
    "name": "NAME",
    "email": "EMAIL",
    "password": "PASSWORD_HASH",
}


def plan(base: Path, users: dict) -> dict[str, tuple[Path, dict]]:
    """The new contents of each user's config, or exit on any conflict."""
    plans = {}
    for user_id, entry in users.items():
        if not (isinstance(user_id, str) and user_id.isalnum()):
            sys.exit(f"User id {user_id!r} must be alphanumeric")
        unknown = set(entry) - set(MOVED_KEYS)
        if unknown:
            sys.exit(f"User {user_id}: don't know where to move {sorted(unknown)}")
        path = user_config_path(user_id, base)
        data = json.loads(path.read_text()) if path.exists() else {}
        for old_key, new_key in MOVED_KEYS.items():
            if old_key not in entry:
                continue
            if new_key in data and data[new_key] != entry[old_key]:
                sys.exit(f"User {user_id}: {path} already has a different {new_key}")
            data[new_key] = entry[old_key]
        plans[user_id] = (path, data)
    return plans


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--base", required=True, type=Path, help="Data directory")
    args = parser.parse_args()

    main_file = args.base / "config.json"
    config = json.loads(main_file.read_text())
    users = config.get("USERS")
    if isinstance(users, list):
        print("USERS is already a list of ids; nothing to do.")
        return
    if not isinstance(users, dict):
        sys.exit("USERS is missing or isn't an object")

    plans = plan(args.base, users)
    for user_id, (path, data) in plans.items():
        if not path.exists():
            path.parent.mkdir(mode=0o700, exist_ok=True)
            path.touch(mode=0o600)
        write_json_atomic(path, data)
        print(f"User {user_id}: login moved to {path}")

    shutil.copy2(main_file, main_file.with_name("config.json.pre-split.bak"))
    config["USERS"] = list(users)
    write_json_atomic(main_file, config)
    print(f"{main_file}: USERS is now {config['USERS']}")


if __name__ == "__main__":
    main()
