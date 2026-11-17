"""
Adds the per-user unique indexes on asset identifiers that the models declare
(instrument location+symbol, payable description, property name, bond name,
deposit certificate name) to an existing database.

It is safe to run more than once: indexes that already exist are skipped. If
any table still holds duplicates, it lists them and changes nothing. Before
changing anything it saves a copy of the database beside it, named
mydatabase.db.<timestamp>.bak.

Usage:
    python -m scripts.add_unique_identifiers --base /path/to/base-dir
    python -m scripts.add_unique_identifiers --base /path/to/base-dir --check
"""

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List

from sqlalchemy import create_engine, inspect, text

from models.bond import Bond
from models.deposit_certificate import DepositCertificate
from models.instrument import Instrument
from models.payable import Payable
from models.property import Property

MODELS = [Instrument, Payable, Property, Bond, DepositCertificate]


def unique_indexes(model):
    return [index for index in model.__table__.indexes if index.unique]


def duplicates(connection, model, index) -> List[str]:
    """Rows of `model` that would break `index`, one line per repeated key."""
    columns = ", ".join(column.name for column in index.columns)
    rows = connection.execute(
        text(
            f"SELECT {columns}, count(*), group_concat(id) "
            f"FROM {model.__tablename__} GROUP BY {columns} HAVING count(*) > 1"
        )
    ).all()
    return [
        f"  {model.__tablename__}: "
        + ", ".join(f"{c.name}={v!r}" for c, v in zip(index.columns, row))
        + f" (ids {row[-1]})"
        for row in rows
    ]


def backup(db_path: Path) -> Path:
    """A consistent copy of the database, via SQLite's backup API."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = db_path.with_name(f"{db_path.name}.{stamp}.bak")
    with sqlite3.connect(db_path) as source, sqlite3.connect(target) as copy:
        source.backup(copy)
    # Same permissions as the database (it is usually readable by its owner only).
    target.chmod(db_path.stat().st_mode & 0o777)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument(
        "--base", type=str, required=True, help="Path to the base directory"
    )
    parser.add_argument(
        "--check", action="store_true", help="Only report; change nothing."
    )
    args = parser.parse_args()

    db_path = Path(args.base) / "mydatabase.db"
    if not db_path.exists():
        raise SystemExit(f"Error: The file '{db_path}' does not exist.")
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")

    existing = {
        model: {
            index["name"] for index in inspect(engine).get_indexes(model.__tablename__)
        }
        for model in MODELS
    }
    missing = [
        (model, index)
        for model in MODELS
        for index in unique_indexes(model)
        if index.name not in existing[model]
    ]
    with engine.connect() as connection:
        problems = [
            line
            for model, index in missing
            for line in duplicates(connection, model, index)
        ]

    if problems:
        print("Duplicates must be renamed or removed first:")
        print("\n".join(problems))
        raise SystemExit(1)
    if not missing:
        print("All unique indexes are already in place.")
        return
    names = ", ".join(index.name for _, index in missing)
    if args.check:
        print(f"No duplicates. Would add: {names}")
        return

    print(f"Backup: {backup(db_path)}")
    for model, index in missing:
        index.create(engine)
        print(f"Added {index.name} on {model.__tablename__}")


if __name__ == "__main__":
    main()
