# Transaction parsers

Plugins for the recurrent transaction bulk import. Each one turns an uploaded
statement into a list of `ParsedTransaction`s that the import UI shows for
review before they're saved.

## Adding a parser

Add a module to this directory that defines a module-level `PARSER`:

```python
from typing import List

from .base import ParsedTransaction, ParseError, TransactionParser


class MyBankParser(TransactionParser):
    id = "my_bank"            # stable id the API uses to pick the parser
    name = "My Bank"
    description = "Monthly statement export"
    extensions = (".pdf",)    # lowercase; other extensions are rejected

    def parse(self, content: bytes, filename: str) -> List[ParsedTransaction]:
        ...  # raise ParseError("...") with a message for the user on bad input


PARSER = MyBankParser()
```

Uploads are limited to the parser's `extensions` (matched ignoring case) and
to `MAX_UPLOAD_BYTES` (1.5 MiB), both checked before `parse` is called.

Modules are discovered on first use (`lib.parsers.available_parsers()`);
`base` and modules starting with `_` are skipped. There's nothing to register.

A parser fills `transaction_date` (`YYYY-MM-DD`), `description` and `amount`
(negative for spending). `year_month` defaults to the transaction date's month.
`recurrent_id` and `paid_with` are optional; the user picks them in the UI when
the source doesn't say.

## Duplicates and ignored rows

`transaction_hashes()` gives each parsed row an import hash from its date,
description, amount and `paid_with`, plus its occurrence number among identical
rows in the same file. Edits made in the UI before importing don't change it.

Each row of a file is imported, ignored or skipped:

- Imported rows store the hash on the `recurrent_transaction`.
- Ignored rows store it in `ignored_transaction`, with the source date,
  description and amount, and aren't counted anywhere.
- Skipped rows store nothing and show up as new next time.

When a file is parsed, rows whose hash is already stored come back with
`status` `imported` (filled in from the saved transaction, read-only in the UI)
or `ignored` (which can still be imported, removing the ignore record).

## Bundled parsers

| id | Input |
|---|---|
| `generic_csv` | CSV/TSV/TXT with a header row using the `recurrentTransactions` field names: `transactionDate`, `description`, `amount` (required), `yearMonth`, `recurrentId`, `paidWithAssetId` (optional). |
| `cuenta_continental` | Banco Continental account statement (`.xlsx`): `FECHAMOVI` is the date, `DESCRIP` the description, `DEBE` a negative amount and `HABER` a positive one. Rows without a date (the `TOTAL` footer) are skipped. |
