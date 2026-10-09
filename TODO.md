# TODO

Follow-ups from the Flask → APIFlask migration.

- [ ] **Add request/response schemas.** Endpoints have no `@app.input` / `@app.output` marshmallow schemas, so the OpenAPI spec lists paths and auth but no body shapes. Add them incrementally, keeping the json-server-style responses (raw lists, `X-Total-Count`) that `ra-data-json-server` expects.
- [ ] **`_sort` / `_order` on list endpoints.** Still missing or partial:

  | Endpoint | Current state |
  |---|---|
  | `/bonds`, `/depositCertificates` | only `name` and `maturityDate` are honoured; any other key silently falls back to name ordering |
  | `/bondSchedules`, `/depositCertificateSchedules` | fixed order by date |
  | `/recurrents`, `/recurrentTransactions`, `/monthlyTransactions`, `/exchangeRates` | fixed order |
  | `/upcoming_payments` | fixed order |
  | list-returning reports | none |

  Add a shared `sort_items()` helper next to `paginate()` (sort before slicing). Things to settle: rows with missing or `None` sort values (the current `x.get(sort_key, "")` can raise on mixed types), `_order` case handling, unknown sort keys (ignore vs 400), and whether DB-backed endpoints sort in SQL or in Python. Add unit tests for the helper and each endpoint touched.
- [ ] **Document cookie auth as its own security scheme.** The spec only lists `BearerAuth`; cookie support is only mentioned in its description. Add a `CookieAuth` (`apiKey`, `in: cookie`) scheme via `SECURITY_SCHEMES` and reference both on protected operations.
- [ ] **Replace the `sys.argv` check for `--debug`.** `init.py` enables the OpenAPI docs by looking for `--debug` in `sys.argv`, because the app is created before argparse runs. Consider an app factory so there is a single source of truth.
- [ ] **Verify the frontend end to end.** The frontend and `mflow-data` were not touched or tested against the migrated backend. Smoke-test login (cookie), the JWT flow and a few react-admin list pages.

## Known bugs

From the 2026-10-09 backend review. Already fixed: recurrent timelines past maturity, recurrents running more than once a month, payables using `amount` (only `balance` counts), dividend and account `factor`, cross-user instrument and recurrent-transaction writes, currency/date/symbol validation, `create_date`, and the `get_returns` / exchange-rate crashes.

### High

- [ ] **`projection_analysis` reads another user's data and crashes easily** (`views/projection.py:39`). `session.query(Recurrent).get(DEFAULT_VAR_ID)` isn't filtered by user, and user 2's config points at `CostoFijo-PY`, which belongs to user 1. It also fails if the recurrent doesn't exist (`None.to_dict()`), raises `KeyError` when that recurrent is in USD (`exchange_for` only has the secondary currency), and divides by zero when `LAST_UNTIL` is less than a month away (`/ runway`, line 56).
- [ ] **`recurrent.identifier` and `account.id` are global primary keys.** Two users can't use the same name: the second POST returns 500 (`UNIQUE constraint failed`), which also tells one user that another user has an asset with that name. A duplicate within your own account also returns 500 instead of 409. Fixing it properly needs a composite key `(user_id, identifier)` and a migration.
- [ ] **Yearly payables only count in their due-date year** for `spending_analysis`, `monthly_pnl` and `projection_analysis` (`Payable.get_budgeted_income`, `asset_classes/payable.py:54`). The future-timeline simulation repeats them every year. Decide whether `due_date` is meant to roll forward when paid, or whether budgets should repeat yearly when `one_off` is false.

### Medium

- [ ] **Numeric fields aren't validated.** `amount`, `balance`, `qty`, `factor`, `capital`, `rate`, prices and so on are saved as given, and `load_assets` calls `float()` on them. A missing or non-numeric value saves, the request returns 500, and every report fails after the next restart (the same pattern the date checks fixed). Missing `flowClass` on payable and recurrent POST crashes on `.lower()` (`rest_assets.py:406`, `rest_recurrents.py:166`).
- [ ] **Hardcoded `USDPYG`** in `list_income` (`views/list_assets.py:50`); use the user's `SECONDARY_CURRENCY`.
- [ ] **Changes can leave dangling targets or orphans.**
  - Deleting an account or instrument, or changing an instrument's location or symbol, doesn't check `target_references`. Changing an account's currency while other assets target it breaks the same-currency rule.
  - Deleting a bond or CD leaves its schedule rows; deleting a recurrent leaves its transactions (8 orphaned transactions in the database as of 2026-10-09). A new recurrent with the same identifier would pick them up.
  - Schedule POST and the CSV uploads (`rest_certificates.py:29`, `:75`) don't check that the bond or CD belongs to the caller or exists.
- [ ] **Monthly P&L summary only totals USD and the secondary currency.** Other configured currencies (e.g. `usdc`) appear in the per-month sums but not in `p_totals` / `n_totals`.
- [ ] **Startup race in `ExchangeRates.ensure_currency_data`** (`data/exchange_rates.py:102`). If the background refresh holds the lock while the cache is still empty, it returns immediately and `exchange_rate` raises.

### Low

- [ ] Crypto quotes are saved to the database with 2 decimals (`data/exchange_rates.py:164`); fine for BTC/ETH/SOL, lossy for low-priced coins after a restart. Re-saving a quote on the same day never updates its value (line 162).
- [ ] Coinbase `estimated_dividend` is in coin units, not USD (`data/coinbase.py:52`).
- [ ] `Property.total_return` converts rent with `USD{rent_currency}`, which assumes the property is priced in USD, and divides by a zero `purchase_price` (`asset_classes/property.py:51`, `:56`).
- [ ] Passwords are stored as unsalted SHA-256 (`models/models.py:116`); move to a salted, slow hash (bcrypt/argon2) with a migration path.
- [ ] `create_date` on recurrent transactions saved before 2026-10-09 holds the server start date, not the real creation date; it can't be recovered.
