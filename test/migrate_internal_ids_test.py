import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine, inspect, text

from scripts import migrate_internal_ids

# The schema before the migration, as the real database had it.
OLD_SCHEMA = """
CREATE TABLE "account" (
    "id" TEXT NOT NULL, "country" TEXT NOT NULL, "institution" TEXT NOT NULL,
    "currency" TEXT NOT NULL, "balance" TEXT NOT NULL, "factor" TEXT NOT NULL,
    "account_type" TEXT NOT NULL, "liquid" INTEGER NOT NULL,
    "user_id" INTEGER NOT NULL DEFAULT 1, transfer_by TEXT, target_asset_id TEXT,
    PRIMARY KEY("id")
);
CREATE INDEX "account_user_id" ON "account" ("user_id");
CREATE TABLE "recurrent" (
    "identifier" TEXT NOT NULL UNIQUE, "parent_asset_id" TEXT,
    "country" TEXT NOT NULL, "amount" TEXT NOT NULL, "currency" TEXT NOT NULL,
    "recurrence" TEXT NOT NULL, "start" TEXT NOT NULL, "end" TEXT NOT NULL,
    "flow_class" TEXT NOT NULL, "rate" TEXT NOT NULL,
    "user_Id" INTEGER NOT NULL DEFAULT 1, target_asset_id TEXT,
    inflation INTEGER NOT NULL DEFAULT 0, PRIMARY KEY("identifier")
);
CREATE TABLE "instrument" (
    "id" INTEGER NOT NULL, "user_id" INTEGER NOT NULL, "country" TEXT NOT NULL,
    "location" TEXT NOT NULL, "symbol" TEXT NOT NULL, "factor" TEXT NOT NULL,
    "qty" TEXT NOT NULL, "dividend" TEXT NOT NULL, "dividend_rate" TEXT NOT NULL,
    "currency" TEXT NOT NULL, "acquisition_date" TEXT NOT NULL,
    "acquisition_price" TEXT NOT NULL, "liquid" INTEGER NOT NULL,
    "capital_rate" TEXT NOT NULL DEFAULT 0, target_asset_id TEXT, sell_by TEXT,
    is_target_pool INTEGER NOT NULL DEFAULT 0, PRIMARY KEY("id")
);
CREATE UNIQUE INDEX instrument_user_location_symbol
    ON instrument (user_id, location, symbol);
CREATE TABLE payable (
    id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, country TEXT NOT NULL,
    currency TEXT NOT NULL, description TEXT NOT NULL, amount TEXT NOT NULL,
    due_date TEXT NOT NULL, commited INTEGER NOT NULL, balance TEXT,
    flow_class TEXT, target_asset_id TEXT
);
CREATE TABLE property (
    id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, property_name TEXT NOT NULL,
    country TEXT NOT NULL, currency TEXT NOT NULL, purchase_price TEXT NOT NULL,
    purchase_date TEXT NOT NULL, current_price TEXT NOT NULL,
    rent_price TEXT NOT NULL, depreciation TEXT NOT NULL,
    additional_data TEXT NOT NULL, rent_currency TEXT NOT NULL, sell_by TEXT,
    target_asset_id TEXT
);
CREATE TABLE bond (
    id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, name TEXT NOT NULL,
    capital TEXT NOT NULL, currency TEXT NOT NULL, maturity_date TEXT NOT NULL,
    rate TEXT NOT NULL, entity TEXT NOT NULL, country TEXT NOT NULL,
    purchase_price TEXT NOT NULL, target_asset_id TEXT
);
CREATE TABLE deposit_certificate (
    id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, name TEXT NOT NULL,
    capital TEXT NOT NULL, currency TEXT NOT NULL, maturity_date TEXT NOT NULL,
    rate TEXT NOT NULL, entity TEXT NOT NULL, country TEXT NOT NULL,
    purchase_price TEXT NOT NULL, target_asset_id TEXT
);
CREATE TABLE recurrent_transaction (
    transaction_id INTEGER PRIMARY KEY, parent_id TEXT NOT NULL,
    year_month TEXT NOT NULL, description TEXT NOT NULL, amount TEXT NOT NULL,
    transaction_date TEXT NOT NULL, paid_with TEXT NOT NULL,
    create_date TEXT NOT NULL, user_id INTEGER NOT NULL, import_hash TEXT
);
"""

ROWS = """
INSERT INTO account VALUES
    ('Checking','US','Citi','USD','10','1','Checking',1,1,NULL,'Puente_USD'),
    ('Theirs','US','Bank','USD','10','1','Checking',1,2,NULL,NULL);
INSERT INTO recurrent VALUES
    ('Rent','Citi_VOO','US','-1','USD','0 0 1 * *','2026-01-01','2030-01-01',
     'expense','0',1,'Puente_USD',0);
INSERT INTO instrument VALUES
    (1,1,'US','Puente','USD','1','1','N','0','USD','2026-01-01','1',1,'0',
     'Puente_USD',NULL,1),
    (2,1,'US','Citi','VOO','1','1','N','0','USD','2026-01-01','1',0,'0',
     'Citi_B5894_USD',NULL,0),
    (3,1,'US','Citi_B5894','USD','1','1','N','0','USD','2026-01-01','1',1,'0',
     'Citi_B5894_USD',NULL,1),
    (4,2,'US','Puente','USD','1','1','N','0','USD','2026-01-01','1',1,'0',
     'Puente_USD',NULL,1);
INSERT INTO payable VALUES
    (1,1,'US','USD','Tax','1','2027-01-01',0,'1','expense','Puente_USD');
INSERT INTO recurrent_transaction VALUES
    (1,'Rent','2026-01','x','-1','2026-01-02','Coinbase_USDC','2026-01-02',1,NULL),
    (2,'Rent','2026-01','y','-1','2026-01-03','Checking','2026-01-03',1,NULL);
"""


class TestMigrateInternalIds(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.base = Path(directory.name)
        self.db = self.base / "mydatabase.db"
        with sqlite3.connect(self.db) as connection:
            connection.executescript(OLD_SCHEMA + ROWS)

    def run_script(self, *flags):
        argv = ["migrate", "--base", str(self.base), *flags]
        with patch("sys.argv", argv), patch("builtins.print") as printed:
            migrate_internal_ids.main()
        return "\n".join(str(c.args[0]) for c in printed.call_args_list)

    def query(self, sql):
        with sqlite3.connect(self.db) as connection:
            return connection.execute(sql).fetchall()

    def test_check_changes_nothing(self):
        output = self.run_script("--check")
        self.assertIn("user 1: Puente_USD -> Puente_TEMP_USD", output)
        self.assertIn("user 1: Coinbase_USDC -> Coinbase_Portfolio_USDC", output)
        self.assertEqual(
            self.query("SELECT location FROM instrument WHERE id = 3"),
            [("Citi_B5894",)],
        )
        self.assertEqual(list(self.base.glob("*.bak")), [])

    def test_migrates_and_rewrites_references(self):
        self.run_script()
        self.assertEqual(len(list(self.base.glob("*.bak"))), 1)
        self.assertEqual(
            self.query(
                "SELECT id, location, account, symbol FROM instrument ORDER BY id"
            ),
            [
                (1, "Puente", "TEMP", "USD"),
                (2, "Citi", "TEMP", "VOO"),
                (3, "Citi", "B5894", "USD"),
                (4, "Puente", "TEMP", "USD"),
            ],
        )
        # Only the owner's references move; the location-embedded account kept
        # its identifier.
        self.assertEqual(
            self.query("SELECT target_asset_id FROM instrument ORDER BY id"),
            [
                ("Puente_TEMP_USD",),
                ("Citi_B5894_USD",),
                ("Citi_B5894_USD",),
                ("Puente_TEMP_USD",),
            ],
        )
        self.assertEqual(
            self.query(
                "SELECT id, location, target_asset_id FROM account ORDER BY internal_id"
            ),
            [("Checking", "Citi", "Puente_TEMP_USD"), ("Theirs", "Bank", None)],
        )
        self.assertEqual(
            self.query("SELECT parent_asset_id, target_asset_id FROM recurrent"),
            [("Citi_TEMP_VOO", "Puente_TEMP_USD")],
        )
        self.assertEqual(
            self.query("SELECT target_asset_id FROM payable"), [("Puente_TEMP_USD",)]
        )
        self.assertEqual(
            self.query(
                "SELECT paid_with FROM recurrent_transaction ORDER BY transaction_id"
            ),
            [("Coinbase_Portfolio_USDC",), ("Checking",)],
        )
        self.assertEqual(
            self.query("SELECT internal_id, id FROM account ORDER BY internal_id"),
            [(1, "Checking"), (2, "Theirs")],
        )
        engine = create_engine(f"sqlite:///{self.db}")
        self.addCleanup(engine.dispose)
        indexes = {
            index["name"]: index["unique"]
            for table in ("account", "recurrent", "instrument", "payable", "bond")
            for index in inspect(engine).get_indexes(table)
        }
        self.assertTrue(indexes["account_user_name"])
        self.assertTrue(indexes["recurrent_user_identifier"])
        self.assertTrue(indexes["instrument_user_location_account_symbol"])
        self.assertTrue(indexes["payable_user_description"])
        self.assertNotIn("instrument_user_location_symbol", indexes)

        # Two users may now share an account name.
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO account (id, country, location, currency, balance,"
                    " factor, account_type, liquid, user_id) VALUES"
                    " ('Checking','US','Bank','USD','1','1','Checking',1,2)"
                )
            )

        self.assertEqual(self.run_script(), "Nothing to do.")

    def test_refuses_duplicates(self):
        with sqlite3.connect(self.db) as connection:
            connection.execute(
                "INSERT INTO instrument VALUES (5,1,'US','Citi_TEMP','VOO','1','1',"
                "'N','0','USD','2026-01-01','1',0,'0',NULL,NULL,0)"
            )
        with self.assertRaises(SystemExit), patch("builtins.print") as printed:
            with patch("sys.argv", ["migrate", "--base", str(self.base)]):
                migrate_internal_ids.main()
        self.assertIn("'Citi_TEMP_VOO'", str(printed.call_args_list))
        self.assertEqual(list(self.base.glob("*.bak")), [])


if __name__ == "__main__":
    unittest.main()
