"""Transaction parser plugins for the recurrent transaction bulk import.

Each module in this package (other than `base` and modules starting with `_`)
is a plugin that defines a module-level `PARSER`, an instance of a
`TransactionParser` subclass. Plugins are discovered and loaded on first use.
"""

import hashlib
import importlib
import pkgutil
from collections import Counter
from typing import Dict, List, Optional

from lib.logger import get_logger

from .base import ParsedTransaction, ParseError, TransactionParser

Logger = get_logger()

_SKIPPED_MODULES = {"base"}
_parsers: Optional[Dict[str, TransactionParser]] = None


def _load_parsers() -> Dict[str, TransactionParser]:
    parsers = {}
    for module_info in pkgutil.iter_modules(__path__):
        name = module_info.name
        if name.startswith("_") or name in _SKIPPED_MODULES:
            continue
        module = importlib.import_module(f"{__name__}.{name}")
        parser = getattr(module, "PARSER", None)
        if not isinstance(parser, TransactionParser) or not parser.id:
            Logger.warning(f"Parser module {name} has no valid PARSER, skipping")
            continue
        if parser.id in parsers:
            Logger.warning(f"Duplicate parser id {parser.id} in {name}, skipping")
            continue
        parsers[parser.id] = parser
    return parsers


def available_parsers() -> Dict[str, TransactionParser]:
    global _parsers
    if _parsers is None:
        _parsers = _load_parsers()
    return _parsers


def get_parser(parser_id: str) -> Optional[TransactionParser]:
    return available_parsers().get(parser_id)


def _identity(transaction: ParsedTransaction) -> str:
    description = " ".join(transaction.description.split())
    return "|".join(
        [
            transaction.transaction_date,
            description,
            repr(float(transaction.amount)),
            transaction.paid_with or "",
        ]
    )


def transaction_hashes(transactions: List[ParsedTransaction]) -> List[str]:
    """One import hash per transaction, so the same row can't be loaded twice.

    The hash covers what the source says (date, description, amount and the
    account, when the source names it), not what the user edits before
    importing. Identical rows in one file (two equal purchases on the same day)
    are told apart by their occurrence number, so both import, while uploading
    the same file again matches every row.
    """
    seen = Counter()
    hashes = []
    for transaction in transactions:
        identity = _identity(transaction)
        occurrence = seen[identity]
        seen[identity] += 1
        hashes.append(
            hashlib.sha256(f"{identity}|{occurrence}".encode("utf-8")).hexdigest()
        )
    return hashes


__all__ = [
    "ParseError",
    "ParsedTransaction",
    "TransactionParser",
    "available_parsers",
    "get_parser",
    "transaction_hashes",
]
