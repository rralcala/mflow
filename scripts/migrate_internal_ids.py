"""
Moves an existing database to per-user asset identifiers:

- account: a new integer primary key `internal_id`; the name (`id`) becomes
  unique per user instead of globally. `institution` is renamed `location`.
- recurrent: a new integer primary key `internal_id`; `identifier` becomes
  unique per user instead of globally.
- instrument: a new `account` column (the account at the location holding it),
  and its identifier becomes Location_Account_Symbol. A location that already
  embeds an account (`Citi_B5894`) is split into location `Citi` and account
  `B5894`; instruments without one get the account `TEMP`, to be fixed by hand.
  Every reference to a renamed instrument (target_asset_id, a recurrent's
  parent_asset_id, a transaction's paid_with) is rewritten, and so are
  references to Coinbase positions, which become Coinbase_Portfolio_<symbol>.
- Adds any missing per-user unique index the models declare (what
  former scripts.add_unique_identifiers did), so it supersedes that script.

It is safe to run more than once: finished steps are skipped. If the result
would hold duplicates it lists them and changes nothing. Before changing
anything it saves a copy of the database beside it, named
mydatabase.db.<timestamp>.bak.

Usage:
    python -m scripts.migrate_internal_ids --base /path/to/base-dir --check
    python -m scripts.migrate_internal_ids --base /path/to/base-dir
"""

import argparse
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from sqlalchemy import create_engine, inspect, text

from lib.util import reference_columns
from models.bond import Bond
from models.deposit_certificate import DepositCertificate
from models.instrument import Instrument, instrument_identifier
from models.models import Account, Recurrent
from models.payable import Payable
from models.property import Property

TEMP_ACCOUNT = "TEMP"
COINBASE_LOCATION = "Coinbase"
COINBASE_ACCOUNT = "Portfolio"  # data/coinbase.py

# Columns holding another asset's identifier.
REFERENCES = reference_columns()
INDEXED = [Account, Recurrent, Instrument, Payable, Property, Bond, DepositCertificate]


def unique_indexes(model):
    return [index for index in model.__table__.indexes if index.unique]


def backup(db_path: Path) -> Path:
    """A consistent copy of the database, via SQLite's backup API."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = db_path.with_name(f"{db_path.name}.{stamp}.bak")
    with sqlite3.connect(db_path) as source, sqlite3.connect(target) as copy:
        source.backup(copy)
    # Same permissions as the database (it is usually readable by its owner only).
    target.chmod(db_path.stat().st_mode & 0o777)
    return target


def columns(connection, table: str) -> List[str]:
    return [c["name"] for c in inspect(connection).get_columns(table)]


def read_rows(connection, table: str) -> List[Dict]:
    rows = connection.execute(text(f'SELECT * FROM "{table}" ORDER BY rowid'))
    return [dict(row._mapping) for row in rows]


def split_location(location: str) -> Tuple[str, str]:
    """`Citi_B5894` is location Citi, account B5894; `Citi` has no account."""
    location, _, account = location.partition("_")
    return location, account or TEMP_ACCOUNT


def plan(connection) -> Dict:
    """What would change, without changing anything."""
    account_cols = columns(connection, "account")
    recurrent_cols = columns(connection, "recurrent")
    instrument_cols = columns(connection, "instrument")
    result = {
        "account": "internal_id" not in account_cols,
        "recurrent": "internal_id" not in recurrent_cols,
        "instrument": "account" not in instrument_cols,
        "renames": {},  # (user_id, old identifier) -> new identifier
        "instruments": [],
    }
    if result["instrument"]:
        for row in read_rows(connection, "instrument"):
            location, account = split_location(row["location"])
            old = f"{row['location']}_{row['symbol']}"
            new = instrument_identifier(location, account, row["symbol"])
            row.update(location=location, account=account)
            result["instruments"].append(row)
            if old != new:
                result["renames"][(row["user_id"], old)] = new
        # Coinbase positions are loaded from its API, not from this table.
        for model, column in REFERENCES:
            table = model.__tablename__
            for user_id, value in connection.execute(
                text(f'SELECT user_id, "{column}" FROM "{table}"')
            ):
                prefix = f"{COINBASE_LOCATION}_"
                if (
                    value
                    and value.startswith(prefix)
                    and value.count("_") == 1
                    and (user_id, value) not in result["renames"]
                ):
                    symbol = value[len(prefix) :]
                    result["renames"][(user_id, value)] = instrument_identifier(
                        COINBASE_LOCATION, COINBASE_ACCOUNT, symbol
                    )
    return result


def duplicates(connection, changes: Dict) -> List[str]:
    """Identifiers that would repeat for a user once migrated."""
    problems = []
    keyed = {
        "account": ("id", read_rows(connection, "account")),
        "recurrent": ("identifier", read_rows(connection, "recurrent")),
    }
    for table, (column, rows) in keyed.items():
        counts = Counter(
            (row.get("user_id", row.get("user_Id")), row[column]) for row in rows
        )
        problems += [
            f"  {table}: user {user} has {count} named {name!r}"
            for (user, name), count in counts.items()
            if count > 1
        ]
    if changes["instrument"]:
        counts = Counter(
            (
                row["user_id"],
                instrument_identifier(row["location"], row["account"], row["symbol"]),
            )
            for row in changes["instruments"]
        )
        problems += [
            f"  instrument: user {user} has {count} named {name!r}"
            for (user, name), count in counts.items()
            if count > 1
        ]
    return problems


def rebuild(connection, model, rows: List[Dict], renamed: Dict[str, str]) -> None:
    """Recreate the model's table from `rows`, keeping only its columns."""
    table = model.__tablename__
    connection.execute(text(f'ALTER TABLE "{table}" RENAME TO "{table}_old"'))
    # Index names are global in SQLite; the old ones would clash with the new.
    for index in inspect(connection).get_indexes(f"{table}_old"):
        connection.execute(text(f'DROP INDEX "{index["name"]}"'))
    model.__table__.create(connection)
    names = {c.name for c in model.__table__.columns}
    payload = []
    for row in rows:
        row = {k.lower() if k == "user_Id" else k: v for k, v in row.items()}
        for old, new in renamed.items():
            if old in row:
                row[new] = row.pop(old)
        payload.append({k: v for k, v in row.items() if k in names})
    if payload:
        connection.execute(model.__table__.insert(), payload)
    connection.execute(text(f'DROP TABLE "{table}_old"'))


def migrate(connection, changes: Dict) -> List[str]:
    log = []
    if changes["account"]:
        rows = read_rows(connection, "account")
        rebuild(connection, Account, rows, {"institution": "location"})
        log.append(
            f"account: added internal_id, institution -> location ({len(rows)} rows)"
        )
    if changes["recurrent"]:
        rows = read_rows(connection, "recurrent")
        rebuild(connection, Recurrent, rows, {})
        log.append(f"recurrent: added internal_id ({len(rows)} rows)")
    if changes["instrument"]:
        rebuild(connection, Instrument, changes["instruments"], {})
        log.append(f"instrument: added account ({len(changes['instruments'])} rows)")
    for (user_id, old), new in sorted(changes["renames"].items()):
        for model, column in REFERENCES:
            result = connection.execute(
                text(
                    f'UPDATE "{model.__tablename__}" SET "{column}" = :new '
                    f'WHERE "{column}" = :old AND user_id = :user_id'
                ),
                {"new": new, "old": old, "user_id": user_id},
            )
            if result.rowcount:
                log.append(
                    f"  user {user_id}: {model.__tablename__}.{column} "
                    f"{old} -> {new} ({result.rowcount})"
                )
    for model, index in missing_indexes(connection):
        index.create(connection)
        log.append(f"Added {index.name} on {model.__tablename__}")
    return log


def missing_indexes(connection) -> List:
    """The models' unique indexes the database lacks (rebuilt tables have theirs)."""
    existing = {
        index["name"]
        for model in INDEXED
        for index in inspect(connection).get_indexes(model.__tablename__)
    }
    return [
        (model, index)
        for model in INDEXED
        for index in unique_indexes(model)
        if index.name not in existing
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--base", required=True, help="Path to the base directory")
    parser.add_argument("--check", action="store_true", help="Only report.")
    args = parser.parse_args()

    db_path = Path(args.base) / "mydatabase.db"
    if not db_path.exists():
        raise SystemExit(f"Error: The file '{db_path}' does not exist.")
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")

    with engine.connect() as connection:
        changes = plan(connection)
        problems = duplicates(connection, changes)
        rebuilt = [t for t in ("account", "recurrent", "instrument") if changes[t]]
        indexes = [
            index.name
            for model, index in missing_indexes(connection)
            if model.__tablename__ not in rebuilt
        ]
    if problems:
        print("Duplicates must be renamed or removed first:")
        print("\n".join(problems))
        raise SystemExit(1)
    if not rebuilt and not indexes:
        print("Nothing to do.")
        return
    if args.check:
        print(f"Would rebuild: {', '.join(rebuilt) or 'nothing'}")
        print(f"Would add indexes: {', '.join(indexes) or 'none'}")
        for (user_id, old), new in sorted(changes["renames"].items()):
            print(f"  user {user_id}: {old} -> {new}")
        return

    print(f"Backup: {backup(db_path)}")
    # pysqlite autocommits DDL outside an explicit transaction; BEGIN by hand so
    # a failure leaves the database untouched.
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.exec_driver_sql("BEGIN")
        try:
            log = migrate(connection, changes)
        except Exception:
            connection.exec_driver_sql("ROLLBACK")
            raise
        connection.exec_driver_sql("COMMIT")
    print("\n".join(log) or "Nothing to do.")


if __name__ == "__main__":
    main()
