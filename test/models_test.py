import unittest
from datetime import datetime
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from data.base import Base
from models.models import RecurrentTransaction


class TestRecurrentTransactionCreateDate(unittest.TestCase):
    def test_create_date_is_set_per_row(self):
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine, tables=[RecurrentTransaction.__table__])
        with Session(engine) as session, patch("models.models.datetime") as clock:
            for day in (1, 2):
                clock.now.return_value = datetime(2030, 1, day)
                session.add(
                    RecurrentTransaction(
                        parent_id="Rent",
                        year_month="2030-01",
                        description="",
                        amount="-100",
                        transaction_date=f"2030-01-0{day}",
                        paid_with="acc-1",
                        user_id=1,
                    )
                )
                session.commit()
            dates = [row.create_date for row in session.query(RecurrentTransaction)]

        self.assertEqual(dates, ["2030-01-01", "2030-01-02"])


if __name__ == "__main__":
    unittest.main()
