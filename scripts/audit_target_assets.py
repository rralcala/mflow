"""
Reports which cash-flow-bearing assets (Bond, DepositCertificate, Recurrent,
Instrument, Payable) are missing a target_asset_id -- the Account/Instrument
that cash is pulled from (cost-bearing flows) or deposited into (income flows).

Usage:
    python -m scripts.audit_target_assets --base /path/to/base-dir
"""

import argparse
from pathlib import Path
from typing import List

from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker

from models.bond import Bond
from models.deposit_certificate import DepositCertificate
from models.instrument import Instrument
from models.models import Recurrent
from models.payable import Payable

ASSET_MODELS = [
    (Bond, "name"),
    (DepositCertificate, "name"),
    (Recurrent, "identifier"),
    (Instrument, "location"),
    (Payable, "description"),
]


def missing_target_rows(session, model, label_field: str) -> List[str]:
    column = model.target_asset_id
    rows = (
        session.query(model)
        .filter(or_(column.is_(None), column == ""))
        .order_by(model.user_id)
        .all()
    )
    return [f"  user_id={row.user_id} id={getattr(row, label_field)!r}" for row in rows]


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit assets missing a target asset.")
    parser.add_argument(
        "--base", type=str, required=True, help="Path to the base directory"
    )
    args = parser.parse_args()

    db_path = Path(args.base) / "mydatabase.db"
    if not db_path.exists():
        raise SystemExit(f"Error: The file '{db_path}' does not exist.")

    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    db_session = sessionmaker(bind=engine)

    with db_session() as session:
        total_missing = 0
        for model, label_field in ASSET_MODELS:
            rows = missing_target_rows(session, model, label_field)
            total_missing += len(rows)
            print(f"{model.__name__}: {len(rows)} missing target_asset_id")
            for line in rows:
                print(line)
        print(f"\nTotal rows missing a target asset: {total_missing}")


if __name__ == "__main__":
    main()
