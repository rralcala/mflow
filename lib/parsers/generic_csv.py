import csv
import math
from io import StringIO
from typing import List

from lib.util import validate_date

from .base import DATE, YEAR_MONTH, ParsedTransaction, ParseError, TransactionParser

# Column names match the recurrentTransactions POST body.
REQUIRED_COLUMNS = ("transactionDate", "description", "amount")
OPTIONAL_COLUMNS = ("yearMonth", "recurrentId", "paidWithAssetId")


class GenericCsvParser(TransactionParser):
    id = "generic_csv"
    name = "Generic CSV"
    description = (
        "Delimited text with a header row. Required columns: "
        + ", ".join(REQUIRED_COLUMNS)
        + ". Optional: "
        + ", ".join(OPTIONAL_COLUMNS)
        + ". Comma, semicolon, tab or pipe separated."
    )
    extensions = (".csv", ".tsv", ".txt")

    def parse(self, content: bytes, filename: str) -> List[ParsedTransaction]:
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise ParseError("File is not UTF-8 text")
        if not text.strip():
            raise ParseError("File is empty")

        try:
            dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        reader = csv.reader(StringIO(text), dialect)
        header = next(reader)

        # Header names are matched ignoring case and surrounding spaces.
        known = {name.lower(): name for name in REQUIRED_COLUMNS + OPTIONAL_COLUMNS}
        columns = [known.get(cell.strip().lower()) for cell in header]
        missing = [name for name in REQUIRED_COLUMNS if name not in columns]
        if missing:
            raise ParseError(f"Missing columns: {', '.join(missing)}")

        transactions = []
        for line, cells in enumerate(reader, start=2):
            if not any(cell.strip() for cell in cells):
                continue
            row = {
                column: cell.strip()
                for column, cell in zip(columns, cells)
                if column is not None
            }
            transactions.append(self._transaction(row, line))
        return transactions

    @staticmethod
    def _transaction(row, line: int) -> ParsedTransaction:
        transaction_date = row.get("transactionDate", "")
        if not DATE.match(transaction_date) or not validate_date(transaction_date):
            raise ParseError(
                f"Line {line}: invalid transactionDate '{transaction_date}',"
                " expected YYYY-MM-DD"
            )
        try:
            amount = float(row.get("amount", ""))
        except ValueError:
            amount = math.nan
        if not math.isfinite(amount):
            raise ParseError(f"Line {line}: invalid amount '{row.get('amount')}'")
        year_month = row.get("yearMonth") or transaction_date[:7]
        if not YEAR_MONTH.match(year_month):
            raise ParseError(
                f"Line {line}: invalid yearMonth '{year_month}', expected YYYY-MM"
            )
        return ParsedTransaction(
            transaction_date=transaction_date,
            description=row.get("description", ""),
            amount=amount,
            year_month=year_month,
            recurrent_id=row.get("recurrentId") or None,
            paid_with=row.get("paidWithAssetId") or None,
        )


PARSER = GenericCsvParser()
