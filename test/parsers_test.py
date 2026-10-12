import unittest
from datetime import datetime
from io import BytesIO

import openpyxl

from lib.parsers import (
    ParsedTransaction,
    ParseError,
    available_parsers,
    get_parser,
    transaction_hashes,
)
from lib.parsers.cuenta_continental import CuentaContinentalParser
from lib.parsers.generic_csv import GenericCsvParser


class TestParserRegistry(unittest.TestCase):
    def test_generic_csv_is_discovered(self):
        self.assertIn("generic_csv", available_parsers())
        self.assertIsInstance(get_parser("generic_csv"), GenericCsvParser)

    def test_unknown_parser(self):
        self.assertIsNone(get_parser("nope"))

    def test_accepts_by_extension(self):
        parser = get_parser("generic_csv")
        self.assertTrue(parser.accepts("a.CSV"))
        self.assertTrue(parser.accepts("dir.v2/a.tsv"))
        self.assertFalse(parser.accepts("a.pdf"))
        self.assertFalse(parser.accepts("csv"))
        self.assertFalse(parser.accepts(""))

    def test_to_dict(self):
        info = get_parser("generic_csv").to_dict()
        self.assertEqual(info["id"], "generic_csv")
        self.assertIn(".csv", info["extensions"])


class TestGenericCsvParser(unittest.TestCase):
    def parse(self, text):
        return GenericCsvParser().parse(text.encode("utf-8"), "file.csv")

    def test_rows_matching_the_post_body(self):
        rows = self.parse(
            "recurrentId,yearMonth,description,amount,transactionDate,paidWithAssetId\n"
            "Rent,2026-09,September rent,-1200.50,2026-10-01,acc-1\n"
        )
        self.assertEqual(
            rows,
            [
                ParsedTransaction(
                    transaction_date="2026-10-01",
                    description="September rent",
                    amount=-1200.5,
                    year_month="2026-09",
                    recurrent_id="Rent",
                    paid_with="acc-1",
                )
            ],
        )

    def test_optional_columns_default(self):
        (row,) = self.parse(
            "transactionDate,description,amount\n2026-10-08,Biggie,-16000\n"
        )
        self.assertEqual(row.year_month, "2026-10")
        self.assertIsNone(row.recurrent_id)
        self.assertIsNone(row.paid_with)

    def test_tab_separated_with_bom_and_loose_header(self):
        (row,) = self.parse(
            "﻿ Amount \tTransactionDate\tdescription\textra\n"
            "-5\t2026-10-08\tCoffee, large\tignored\n"
        )
        self.assertEqual(row.amount, -5.0)
        self.assertEqual(row.description, "Coffee, large")

    def test_semicolon_and_blank_lines(self):
        rows = self.parse(
            "transactionDate;description;amount\n\n2026-10-08;A;1\n;;\n2026-10-09;B;2\n"
        )
        self.assertEqual([row.description for row in rows], ["A", "B"])

    def test_missing_column(self):
        with self.assertRaisesRegex(ParseError, "Missing columns: amount"):
            self.parse("transactionDate,description\n2026-10-08,A\n")

    def test_bad_date(self):
        with self.assertRaisesRegex(ParseError, "Line 2: invalid transactionDate"):
            self.parse("transactionDate,description,amount\n2026-10-8,A,1\n")

    def test_bad_amount(self):
        for amount in ("abc", "", "nan"):
            with self.assertRaisesRegex(ParseError, "Line 2: invalid amount"):
                self.parse(
                    f"transactionDate,description,amount\n2026-10-08,A,{amount}\n"
                )

    def test_bad_year_month(self):
        with self.assertRaisesRegex(ParseError, "invalid yearMonth"):
            self.parse(
                "transactionDate,description,amount,yearMonth\n2026-10-08,A,1,2026-13\n"
            )

    def test_empty_and_binary(self):
        with self.assertRaisesRegex(ParseError, "empty"):
            self.parse("  \n")
        with self.assertRaisesRegex(ParseError, "UTF-8"):
            GenericCsvParser().parse(b"\xff\xfe\x00", "x.csv")


HEADER = ["DIACONT", "FECHA", "DESCRIP", "DEBE", "HABER", "SALDO", "FECHAMOVI"]


def workbook(rows, header=HEADER, title_rows=()):
    book = openpyxl.Workbook()
    sheet = book.active
    for row in [*title_rows, header, *rows]:
        sheet.append(row)
    buffer = BytesIO()
    book.save(buffer)
    return buffer.getvalue()


class TestCuentaContinentalParser(unittest.TestCase):
    def parse(self, content):
        return CuentaContinentalParser().parse(content, "Extracto Cuenta.xlsx")

    def test_registered(self):
        parser = get_parser("cuenta_continental")
        self.assertEqual(parser.name, "Cuenta-Continental")
        self.assertTrue(parser.accepts("Extracto Cuenta.XLSX"))
        self.assertFalse(parser.accepts("extracto.csv"))

    def test_debe_is_spending_and_haber_income(self):
        rows = self.parse(
            workbook(
                [
                    [
                        "01",
                        "10:14",
                        "TRF.INTRBN  IN",
                        " ",
                        200000,
                        "884.742",
                        datetime(2026, 10, 1),
                    ],
                    [
                        "02",
                        "09:05",
                        "Mov.POS.:SHOP",
                        1400000,
                        " ",
                        "1.000",
                        datetime(2026, 10, 2),
                    ],
                    # The bank's footer row has no date.
                    [None, None, "TOTAL", None, None, None, None],
                ]
            )
        )
        self.assertEqual(
            rows,
            [
                ParsedTransaction(
                    transaction_date="2026-10-01",
                    description="TRF.INTRBN IN",
                    amount=200000.0,
                    year_month="2026-10",
                ),
                ParsedTransaction(
                    transaction_date="2026-10-02",
                    description="Mov.POS.:SHOP",
                    amount=-1400000.0,
                    year_month="2026-10",
                ),
            ],
        )

    def test_text_amounts_dates_and_title_rows(self):
        (row,) = self.parse(
            workbook(
                [["01", "", "Cambio", "1.234.567,50", "", "", "31/10/2026"]],
                title_rows=[["Extracto de cuenta"], []],
            )
        )
        self.assertEqual((row.transaction_date, row.amount), ("2026-10-31", -1234567.5))

    def test_errors(self):
        cases = {
            "Missing header row": workbook([], header=["FECHA", "DESCRIP"]),
            "Line 2: expected either DEBE or HABER": workbook(
                [["01", "", "x", 1, 2, "", datetime(2026, 10, 1)]]
            ),
            "Line 2: invalid HABER 'abc'": workbook(
                [["01", "", "x", " ", "abc", "", datetime(2026, 10, 1)]]
            ),
            "Line 2: invalid FECHAMOVI '2026-13-01'": workbook(
                [["01", "", "x", 1, " ", "", "2026-13-01"]]
            ),
        }
        for message, content in cases.items():
            with self.assertRaisesRegex(ParseError, message):
                self.parse(content)
        with self.assertRaisesRegex(ParseError, "not a valid .xlsx"):
            self.parse(b"transactionDate,description,amount\n")


class TestTransactionHashes(unittest.TestCase):
    def tx(self, **overrides):
        fields = dict(
            transaction_date="2026-10-08", description="Biggie", amount=-16000
        )
        fields.update(overrides)
        return ParsedTransaction(**fields)

    def test_stable_and_ignores_assignment(self):
        first = transaction_hashes([self.tx()])
        again = transaction_hashes(
            [self.tx(amount=-16000.0, description=" Biggie ", recurrent_id="Food")]
        )
        self.assertEqual(first, again)
        self.assertRegex(first[0], r"^[0-9a-f]{64}$")

    def test_source_fields_change_the_hash(self):
        base = transaction_hashes([self.tx()])[0]
        for change in (
            dict(transaction_date="2026-10-09"),
            dict(description="Stock"),
            dict(amount=-16001),
            dict(paid_with="visa"),
        ):
            self.assertNotEqual(transaction_hashes([self.tx(**change)])[0], base)

    def test_identical_rows_get_distinct_hashes(self):
        hashes = transaction_hashes([self.tx(), self.tx(), self.tx(description="x")])
        self.assertEqual(len(set(hashes)), 3)
        # The first occurrence matches a file holding the row once.
        self.assertEqual(hashes[0], transaction_hashes([self.tx()])[0])


if __name__ == "__main__":
    unittest.main()
