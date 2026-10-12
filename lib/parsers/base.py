import os
import re
from dataclasses import dataclass
from typing import List, Optional

DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
YEAR_MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

# Largest file the import accepts, for every parser (1.5 MiB).
MAX_UPLOAD_BYTES = 1536 * 1024


class ParseError(ValueError):
    """The file can't be read by the parser; the message is shown to the user."""


@dataclass
class ParsedTransaction:
    """A transaction read from a statement, before it's assigned to a recurrent.

    `recurrent_id` and `paid_with` are optional: a parser fills them only when
    the source names them, and the import UI lets the user set or change them.
    """

    transaction_date: str
    description: str
    amount: float
    year_month: Optional[str] = None
    recurrent_id: Optional[str] = None
    paid_with: Optional[str] = None


class TransactionParser:
    """Base class for transaction parser plugins.

    A plugin is a module in `lib/parsers/` that defines a module-level
    `PARSER` instance of a subclass of this class.
    """

    # Stable id, used by the API to pick the parser.
    id: str = ""
    name: str = ""
    description: str = ""
    # Lowercase file extensions (with the dot) the parser accepts; uploads
    # with any other extension are rejected.
    extensions: tuple = ()

    def parse(self, content: bytes, filename: str) -> List[ParsedTransaction]:
        raise NotImplementedError

    def accepts(self, filename: str) -> bool:
        return os.path.splitext(filename)[1].lower() in self.extensions

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "extensions": list(self.extensions),
            "maxBytes": MAX_UPLOAD_BYTES,
        }
