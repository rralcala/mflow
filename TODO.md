# TODO

Follow-ups from the Flask → APIFlask migration.

- [ ] **Response schemas for the analytic reports.** Every endpoint now has request schemas (bodies and query args, in `routes/schemas.py`), and every resource and list report has a response schema. These reports still return undocumented payloads: `assets_by_location`, `cash_flow`, `future_timeline`, `income_per_location`, `investment_performance`, `monthly_pnl`, `nw_summary`, `recurrent_history`, `spending_analysis`, `valuation_history`. Several use dynamic keys (`cash_flow`'s `USD-US` columns) or rows as lists (`nw_summary`'s `tot_per_location`), so they need `Dict` / `List` fields or a reshaped payload agreed with the dashboards. Output schemas drop undeclared keys: add a dump round-trip test against real view output for each (see `test/schemas_test.py`), and remove the report from `UNDOCUMENTED_RESPONSES` there.
- [ ] **`_sort` / `_order` on list endpoints.** Still missing or partial:

  | Endpoint | Current state |
  |---|---|
  | `/bonds`, `/depositCertificates` | only `name` and `maturityDate` are honoured; any other key silently falls back to name ordering |
  | `/bondSchedules`, `/depositCertificateSchedules` | fixed order by date |
  | `/recurrents`, `/recurrentTransactions`, `/monthlyTransactions`, `/exchangeRates` | fixed order |
  | `/upcoming_payments` | fixed order |
  | list-returning reports | none |

  Add a shared `sort_items()` helper next to `paginate()` (sort before slicing). Things to settle: rows with missing or `None` sort values (the current `x.get(sort_key, "")` can raise on mixed types), `_order` case handling, unknown sort keys (ignore vs 400), and whether DB-backed endpoints sort in SQL or in Python. Add unit tests for the helper and each endpoint touched.

## Known bugs

### High

- [ ] **`recurrent.identifier` and `account.id` are global primary keys.** Two users can't use the same name: the second POST returns 500 (`UNIQUE constraint failed`), which also tells one user that another user has an asset with that name. A duplicate within your own account also returns 500 instead of 409. Fixing it properly needs a composite key `(user_id, identifier)` and a migration.

### Medium

- [ ] **Hardcoded `USDPYG`** in `list_income` (`views/list_assets.py:50`); use the user's `SECONDARY_CURRENCY`.
- [ ] **Changes can leave dangling targets or orphans.**
  - Deleting an account or instrument, or changing an instrument's location or symbol, doesn't check `target_references`. Changing an account's currency while other assets target it breaks the same-currency rule.
  - Deleting a bond or CD leaves its schedule rows; deleting a recurrent leaves its transactions (8 orphaned transactions in the database as of 2026-10-09). A new recurrent with the same identifier would pick them up.
  - Schedule POST and the CSV uploads (`rest_certificates.py:29`, `:75`) don't check that the bond or CD belongs to the caller or exists.
- [ ] **Monthly P&L summary only totals USD and the secondary currency.** Other configured currencies (e.g. `usdc`) appear in the per-month sums but not in `p_totals` / `n_totals`.

### Low

- [ ] Crypto quotes are saved to the database with 2 decimals (`data/exchange_rates.py:164`); fine for BTC/ETH/SOL, lossy for low-priced coins after a restart. Re-saving a quote on the same day never updates its value (line 162).
- [ ] Coinbase `estimated_dividend` is in coin units, not USD (`data/coinbase.py:52`).
- [ ] `Property.total_return` converts rent with `USD{rent_currency}`, which assumes the property is priced in USD, and divides by a zero `purchase_price` (`asset_classes/property.py:51`, `:56`).
- [ ] Passwords are stored as unsalted SHA-256 (`models/models.py:116`); move to a salted, slow hash (bcrypt/argon2) with a migration path.
- [ ] `create_date` on recurrent transactions saved before 2026-10-09 holds the server start date, not the real creation date; it can't be recovered.
