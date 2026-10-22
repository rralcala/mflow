"""
Sets user passwords, stored as salted scrypt hashes in each user's
user-<id>/config.json (the user ids come from the main config.json's USERS).

The password is read from the terminal (or from stdin when piped), never from
the command line, so it doesn't end up in shell history or `ps` output.
Restart the API afterwards: running servers keep the hashes they loaded.

Usage:
    python -m scripts.set_passwords --base /path/to/base-dir --user 1
    python -m scripts.set_passwords --base /path/to/base-dir --all
"""

import argparse
import getpass
import json
import sys
from pathlib import Path

from lib.passwords import hash_password, password_problem, set_password_hash


def read_password() -> str:
    if sys.stdin.isatty():
        password = getpass.getpass("New password: ")
        if getpass.getpass("Repeat: ") != password:
            sys.exit("Passwords don't match.")
        return password
    return sys.stdin.readline().rstrip("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--base", required=True, type=Path, help="Data directory")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--user", action="append", help="User id (repeatable)")
    target.add_argument("--all", action="store_true", help="Every user")
    args = parser.parse_args()

    users = json.loads((args.base / "config.json").read_text()).get("USERS")
    if not isinstance(users, list):
        sys.exit("USERS isn't a list of ids; run scripts.split_user_config first")
    user_ids = users if args.all else args.user
    unknown = [uid for uid in user_ids if uid not in users]
    if unknown:
        sys.exit(f"Unknown user id(s): {unknown}")

    password = read_password()
    problem = password_problem(password)
    if problem:
        sys.exit(problem)

    for user_id in user_ids:  # each user gets their own salt
        set_password_hash(user_id, hash_password(password), args.base)
    print(f"Updated password for user(s): {', '.join(user_ids)}")


if __name__ == "__main__":
    main()
