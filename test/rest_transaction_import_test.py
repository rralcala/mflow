import io
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from data.base import Base
from lib.config import Config
from models.models import IgnoredTransaction, Recurrent, RecurrentTransaction
from routes.assets import rest_recurrents

CSV = (
    b"transactionDate,description,amount,paidWithAssetId\n"
    b"2026-10-08,Biggie,-16000,visa\n"
    b"2026-10-08,Biggie,-16000,visa\n"
    b"2026-10-09,Stock,-5000,visa\n"
)


def recurrent(identifier, user_id):
    return Recurrent(
        identifier=identifier,
        country="PY",
        amount="-100",
        currency="PYG",
        recurrence="0 0 1 * *",
        start="2026-01-01",
        end="2030-01-01",
        flow_class="expense",
        rate="0",
        user_id=user_id,
    )


class TestRecurrentTransactionImport(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        engine = create_engine("sqlite://")
        self.addCleanup(engine.dispose)
        Base.metadata.create_all(
            engine,
            tables=[
                Recurrent.__table__,
                RecurrentTransaction.__table__,
                IgnoredTransaction.__table__,
            ],
        )
        self.Session = sessionmaker(bind=engine)
        with self.Session() as session:
            session.add_all([recurrent("Food", 1), recurrent("Theirs", 2)])
            session.commit()
        for target in (
            patch.object(Config, "DB_SESSION", self.Session, create=True),
            patch.object(rest_recurrents, "current_user", SimpleNamespace(id="1")),
            patch.object(rest_recurrents, "reload_asset_store"),
            patch.object(rest_recurrents.UserStore, "get_user_config"),
        ):
            target.start()
            self.addCleanup(target.stop)

    def parse(self, content=CSV, parser="generic_csv", filename="statement.csv"):
        data = {"parser": parser, "file": (io.BytesIO(content), filename)}
        with self.app.test_request_context(
            "/recurrentTransactionsParse",
            method="POST",
            data=data,
            content_type="multipart/form-data",
        ):
            response, status = (
                rest_recurrents.recurrent_transactions_parse.__wrapped__()
            )
        return response.get_json(), status

    def import_rows(self, rows, ignored=None):
        with self.app.test_request_context(
            "/recurrentTransactionsImport",
            method="POST",
            json={"transactions": rows, "ignored": ignored or []},
        ):
            response, status = (
                rest_recurrents.recurrent_transactions_import.__wrapped__()
            )
        return response.get_json(), status

    def assigned(self, rows, recurrent_id="Food"):
        return [dict(row, recurrentId=recurrent_id) for row in rows]

    def test_lists_parsers(self):
        with self.app.test_request_context("/transactionParsers"):
            response, status = rest_recurrents.transaction_parsers.__wrapped__()
        self.assertEqual(status, 200)
        parsers = {p["id"]: p for p in response.get_json()}
        self.assertEqual(parsers["generic_csv"]["maxBytes"], 1536 * 1024)

    def test_parse_returns_rows_with_hashes(self):
        rows, status = self.parse()
        self.assertEqual(status, 200)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["yearMonth"], "2026-10")
        self.assertEqual(rows[0]["paidWithAssetId"], "visa")
        self.assertEqual(len({row["importHash"] for row in rows}), 3)
        self.assertEqual({row["status"] for row in rows}, {"new"})
        self.assertIsNone(rows[0]["transactionId"])

    def test_parse_errors(self):
        body, status = self.parse(parser="nope")
        self.assertEqual((status, body["message"]), (400, "Unknown parser"))
        body, status = self.parse(content=b"description\nx\n")
        self.assertEqual(status, 400)
        self.assertIn("Missing columns", body["message"])

    def test_parse_accepts_only_the_parser_extensions(self):
        for filename in ("statement.pdf", "statement", "csv"):
            body, status = self.parse(filename=filename)
            self.assertEqual(status, 400, filename)
            self.assertIn(".csv, .tsv, .txt", body["message"])
        for filename in ("STATEMENT.CSV", "s.tsv", "s.txt"):
            _, status = self.parse(filename=filename)
            self.assertEqual(status, 200, filename)

    def test_parse_size_limit(self):
        header = b"transactionDate,description,amount\n"
        row = b"2026-10-08,Biggie,-16000\n"
        limit = 1536 * 1024
        rows = (limit - len(header)) // len(row)
        padding = b" " * (limit - len(header) - rows * len(row))
        at_limit = header + row * rows + padding
        self.assertEqual(len(at_limit), limit)
        _, status = self.parse(content=at_limit)
        self.assertEqual(status, 200)
        body, status = self.parse(content=at_limit + b"\n")
        self.assertEqual((status, body["message"]), (413, "File is larger than 1.5 MB"))

    def test_import_then_reimport_skips_everything(self):
        rows, _ = self.parse()
        body, status = self.import_rows(self.assigned(rows))
        self.assertEqual(
            (status, body), (201, {"inserted": 3, "ignored": 0, "skipped": 0})
        )

        with self.Session() as session:
            saved = session.query(RecurrentTransaction).all()
            self.assertEqual(len(saved), 3)
            self.assertEqual(saved[0].parent_id, "Food")
            self.assertEqual(saved[0].year_month, "2026-10")
            self.assertEqual(saved[0].amount, "-16000.0")
            self.assertEqual(saved[0].import_hash, rows[0]["importHash"])

        again, _ = self.parse()
        self.assertEqual({row["status"] for row in again}, {"imported"})
        body, status = self.import_rows(self.assigned(again))
        self.assertEqual(
            (status, body), (201, {"inserted": 0, "ignored": 0, "skipped": 3})
        )

    def test_import_keeps_user_edits(self):
        rows, _ = self.parse()
        edited = dict(rows[0], recurrentId="Food", description="Groceries", amount=-1)
        self.import_rows([edited, edited])  # repeated hash in one batch: once
        with self.Session() as session:
            (saved,) = session.query(RecurrentTransaction).all()
        self.assertEqual((saved.description, saved.amount), ("Groceries", "-1.0"))

    def test_hashes_are_per_user(self):
        rows, _ = self.parse()
        with self.Session() as session:
            session.add(
                RecurrentTransaction(
                    parent_id="Theirs",
                    year_month="2026-10",
                    description="Biggie",
                    amount="-16000",
                    transaction_date="2026-10-08",
                    paid_with="visa",
                    user_id=2,
                    import_hash=rows[0]["importHash"],
                )
            )
            session.commit()
        again, _ = self.parse()
        self.assertEqual(again[0]["status"], "new")
        body, _ = self.import_rows(self.assigned(again[:1]))
        self.assertEqual(body["inserted"], 1)

    def test_invalid_rows_reject_the_whole_batch(self):
        rows, _ = self.parse()
        good = self.assigned(rows)
        cases = {
            "unknown recurrent 'Theirs'": dict(good[1], recurrentId="Theirs"),
            "invalid importHash": dict(good[1], importHash="abc"),
            "invalid transactionDate": dict(good[1], transactionDate="2026-1-5"),
            "invalid yearMonth": dict(good[1], yearMonth="2026-13"),
            "invalid amount": dict(good[1], amount="x"),
            "missing paidWithAssetId": dict(good[1], paidWithAssetId=None),
            "description longer than 200": dict(good[1], description="x" * 201),
        }
        for message, bad in cases.items():
            body, status = self.import_rows([good[0], bad])
            self.assertEqual(status, 400, message)
            self.assertIn(f"Transaction 2: {message}", body["message"])
        with self.Session() as session:
            self.assertEqual(session.query(RecurrentTransaction).count(), 0)

        body, status = self.import_rows([])
        self.assertEqual((status, body["message"]), (400, "No transactions"))

    def test_invalid_ignored_rows_reject_the_whole_batch(self):
        rows, _ = self.parse()
        good = self.assigned(rows)
        # Rows to ignore don't need a recurrent or an account.
        bare = {
            key: rows[1][key] for key in ("importHash", "transactionDate", "amount")
        }
        for bad in (dict(bare, importHash="x"), dict(bare, amount="nan")):
            body, status = self.import_rows([good[0]], ignored=[bare, bad])
            self.assertEqual(status, 400)
            self.assertIn("Ignored row 2:", body["message"])
        with self.Session() as session:
            self.assertEqual(session.query(RecurrentTransaction).count(), 0)
            self.assertEqual(session.query(IgnoredTransaction).count(), 0)

    def test_ignored_rows_are_remembered(self):
        rows, _ = self.parse()
        body, status = self.import_rows(self.assigned(rows[:1]), ignored=rows[1:])
        self.assertEqual(
            (status, body), (201, {"inserted": 1, "ignored": 2, "skipped": 0})
        )
        with self.Session() as session:
            saved = session.query(IgnoredTransaction).order_by("id").all()
            self.assertEqual(
                [(row.transaction_date, row.description, row.amount) for row in saved],
                [
                    ("2026-10-08", "Biggie", "-16000.0"),
                    ("2026-10-09", "Stock", "-5000.0"),
                ],
            )

        again, _ = self.parse()
        self.assertEqual(
            [row["status"] for row in again], ["imported", "ignored", "ignored"]
        )
        # Ignoring again, or ignoring an imported row, changes nothing.
        body, _ = self.import_rows([], ignored=again)
        self.assertEqual(body, {"inserted": 0, "ignored": 0, "skipped": 3})

    def test_importing_an_ignored_row_unignores_it(self):
        rows, _ = self.parse()
        self.import_rows([], ignored=rows[2:])
        body, _ = self.import_rows(self.assigned(rows[2:]))
        self.assertEqual(body, {"inserted": 1, "ignored": 0, "skipped": 0})
        with self.Session() as session:
            self.assertEqual(session.query(IgnoredTransaction).count(), 0)
        again, _ = self.parse()
        self.assertEqual(again[2]["status"], "imported")

    def test_import_wins_over_ignore_in_one_batch(self):
        rows, _ = self.parse()
        body, _ = self.import_rows(self.assigned(rows[:1]), ignored=rows[:1])
        self.assertEqual(body, {"inserted": 1, "ignored": 0, "skipped": 1})

    def test_parse_prefills_imported_rows_from_the_database(self):
        rows, _ = self.parse()
        edited = dict(
            rows[0],
            recurrentId="Food",
            description="Groceries",
            amount=-1,
            yearMonth="2026-09",
            paidWithAssetId="cash",
        )
        self.import_rows([edited])
        with self.Session() as session:
            transaction_id = session.query(RecurrentTransaction).one().transaction_id

        again, _ = self.parse()
        self.assertEqual(
            again[0],
            {
                "importHash": rows[0]["importHash"],
                "transactionDate": "2026-10-08",
                "yearMonth": "2026-09",
                "description": "Groceries",
                "amount": -1.0,
                "recurrentId": "Food",
                "paidWithAssetId": "cash",
                "status": "imported",
                "transactionId": transaction_id,
            },
        )
        # The second, identical file row is still new.
        self.assertEqual(again[1]["status"], "new")
        self.assertEqual(again[1]["description"], "Biggie")


if __name__ == "__main__":
    unittest.main()
