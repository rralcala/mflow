import math
import re
import zipfile
from datetime import date, datetime
from io import BytesIO
from typing import List

import openpyxl
from openpyxl.utils.exceptions import InvalidFileException

from .base import ParsedTransaction, ParseError, TransactionParser

DESCRIPTION = "DESCRIP"
DATE = "FECHAMOVI"
DEBIT = "DEBE"
CREDIT = "HABER"
REQUIRED_COLUMNS = (DESCRIPTION, DATE, DEBIT, CREDIT)

# The header is the first row, but allow for a few title rows above it.
HEADER_SEARCH_ROWS = 20
DATE_FORMATS = ("%d/%m/%Y", "%Y-%m-%d")


def _blank(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _amount(value, column: str, line: int) -> float:
    """Numbers come as numbers, or as text in local format: 1.234.567,50."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        amount = float(value)
    else:
        text = str(value).strip().replace(".", "").replace(",", ".")
        try:
            amount = float(text)
        except ValueError:
            amount = math.nan
    if not math.isfinite(amount) or amount < 0:
        raise ParseError(f"Line {line}: invalid {column} '{value}'")
    return amount


def _date(value, line: int) -> str:
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(str(value).strip(), date_format).strftime(
                "%Y-%m-%d"
            )
        except ValueError:
            pass
    raise ParseError(f"Line {line}: invalid {DATE} '{value}'")


class CuentaContinentalParser(TransactionParser):
    id = "cuenta_continental"
    name = "Cuenta-Continental"
    description = (
        "Banco Continental account statement (.xlsx). Uses FECHAMOVI as the "
        "date, DESCRIP as the description, DEBE as spending and HABER as income."
    )
    extensions = (".xlsx",)

    def parse(self, content: bytes, filename: str) -> List[ParsedTransaction]:
        try:
            workbook = openpyxl.load_workbook(
                BytesIO(content), read_only=True, data_only=True
            )
        except (InvalidFileException, zipfile.BadZipFile, KeyError, OSError):
            raise ParseError("File is not a valid .xlsx workbook")
        try:
            rows = workbook.worksheets[0].iter_rows(values_only=True)
            columns = self._find_header(rows)
            transactions = []
            # Data starts on the line after the header.
            for line, cells in enumerate(rows, start=columns["_line"] + 1):
                transaction = self._transaction(cells, columns, line)
                if transaction is not None:
                    transactions.append(transaction)
        finally:
            workbook.close()
        return transactions

    @staticmethod
    def _find_header(rows):
        for line, cells in enumerate(rows, start=1):
            names = [str(cell).strip().upper() if cell else "" for cell in cells]
            if all(column in names for column in REQUIRED_COLUMNS):
                columns = {column: names.index(column) for column in REQUIRED_COLUMNS}
                columns["_line"] = line
                return columns
            if line >= HEADER_SEARCH_ROWS:
                break
        raise ParseError(f"Missing header row with {', '.join(REQUIRED_COLUMNS)}")

    @staticmethod
    def _transaction(cells, columns, line: int):
        def cell(column):
            index = columns[column]
            return cells[index] if index < len(cells) else None

        # Rows without a date are blank lines or the TOTAL footer.
        if _blank(cell(DATE)):
            return None
        debit, credit = cell(DEBIT), cell(CREDIT)
        if _blank(debit) == _blank(credit):
            raise ParseError(f"Line {line}: expected either {DEBIT} or {CREDIT}")
        if _blank(credit):
            amount = -_amount(debit, DEBIT, line)
        else:
            amount = _amount(credit, CREDIT, line)
        transaction_date = _date(cell(DATE), line)
        description = "" if _blank(cell(DESCRIPTION)) else str(cell(DESCRIPTION))
        return ParsedTransaction(
            transaction_date=transaction_date,
            description=" ".join(description.split())[:200],
            amount=amount,
            year_month=transaction_date[:7],
        )


PARSER = CuentaContinentalParser()
