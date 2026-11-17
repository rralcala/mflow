# TODO

Follow-ups from the Flask → APIFlask migration.

- [ ] **Response schemas for the analytic reports.** Every endpoint now has request schemas (bodies and query args, in `routes/schemas.py`), and every resource and list report has a response schema. These reports still return undocumented payloads: `assets_by_location`, `cash_flow`, `future_timeline`, `income_per_location`, `investment_performance`, `monthly_pnl`, `nw_summary`, `recurrent_history`, `spending_analysis`, `valuation_history`. Several use dynamic keys (`cash_flow`'s `USD-US` columns) or rows as lists (`nw_summary`'s `tot_per_location`), so they need `Dict` / `List` fields or a reshaped payload agreed with the dashboards. Output schemas drop undeclared keys: add a dump round-trip test against real view output for each (see `test/schemas_test.py`), and remove the report from `UNDOCUMENTED_RESPONSES` there.
- [x] **`_sort` / `_order` on list endpoints.** `sort_items()` (`lib/util.py`, next to `paginate()`) sorts in Python on the API field names, before slicing. `_sort` must be a field of the endpoint's output schema (400 otherwise); `_order` is ASC/DESC in any case; missing or `None` values go last in both directions; numbers sort before strings so mixed types don't raise, and strings compare case-insensitively. Each endpoint keeps its old order as the default when `_sort` is absent. Covers accounts, assets, instruments, payables, properties, bonds, CDs, both schedule lists, recurrents, recurrent transactions, monthly transactions, exchange rates and upcoming payments. Frontend lists whose order used to come from a backend remap of `id` now ask for it explicitly. Left as is: `dashboardBudgets` (config order) and `transactionParsers`; the list-shaped reports return chart rows the dashboards fetch directly, not react-admin records.

## Planned

- [ ] **Migrate login auth to WorkOS (AuthKit).** Replace the password check in `user-<id>/config.json` (`/auth/rlogin`, `/auth/login`, `find_user_by_username`) with WorkOS sign-in, and map each WorkOS user to an mflow user id. Decide what happens to `/auth/jwt` Bearer tokens (keep them for scripts such as the mflow-api skill, or verify WorkOS access tokens instead). The frontend's `authProvider.ts` needs the matching redirect flow. This is also the OAuth server a remote MCP connector would use (dynamic client registration), and it would retire the local password store (`PASSWORD_HASH` in each `user-<id>/config.json`, scrypt-hashed).

## Known bugs

### High

- [ ] **`recurrent.identifier` and `account.id` are global primary keys.** Two users can't use the same name. A duplicate within your own account is now refused up front (409, "An asset named … already exists"); a name another user holds still fails at the database, now as a generic 409 ("Conflicts with an existing record") instead of a 500, but that still tells one user another has the name and blocks them from using it. Fixing it properly needs a composite key `(user_id, identifier)` and a migration (rebuilding both tables in SQLite).

### Medium

- [x] **Hardcoded `USDPYG`** in `list_income` (`views/list_assets.py:50`); use the user's `SECONDARY_CURRENCY`.
- [x] **Changes can leave dangling targets or orphans.** Deletes now return 409 while other assets target the asset or recurrents are attached to it, while a bond/CD has schedule rows, or while a recurrent has transactions. Renames (instrument location/symbol, property name, payable description, bond/CD name) and an account currency change are refused (400) while used. Schedule POSTs and a recurrent's `assetId` must belong to the caller. `DELETE /bondSchedules/<id>` and `DELETE /depositCertificateSchedules/<id>` added so a bond/CD can be emptied before deleting it.
- [x] **Asset identifiers aren't unique, and several places assume they are.** Identifiers are now unique per user across every asset type. Creates and renames (accounts, instruments, payables, properties, bonds, CDs, recurrents) are refused with a 409 when another of the user's assets already has the identifier (`duplicate_error` in `lib/util.py`). Unique indexes back this up per table: `instrument (user_id, location, symbol)`, `payable (user_id, description)`, `property (user_id, property_name)`, `bond (user_id, name)`, `deposit_certificate (user_id, name)`; any `IntegrityError` becomes a 409. Uniqueness across types is enforced by the routes only. The code that assumed unique identifiers (Future Timeline `targets` / `sale_dates`, `validate_pool_target`, `target_country`, `GET /assets/<id>`, row ids in Upcoming Payments and Monthly Transactions, frontend selectors and keys) is left as is, since duplicates can no longer be created.
  - Existing databases need the indexes added with `python -m scripts.add_unique_identifiers --base <dir>` (`--check` for a dry run). It refuses to run while duplicates exist and saves a `.bak` copy first. Applied to the local `mflow-data/mydatabase.db` on 2026-11-17; **still to run on the server**.
- [ ] **Monthly P&L summary only totals USD and the secondary currency.** Other configured currencies (e.g. `usdc`) appear in the per-month sums but not in `p_totals` / `n_totals`.

### Low

- [ ] Crypto quotes are saved to the database with 2 decimals (`data/exchange_rates.py:164`); fine for BTC/ETH/SOL, lossy for low-priced coins after a restart. Re-saving a quote on the same day never updates its value (line 162).
- [ ] Coinbase `estimated_dividend` is in coin units, not USD (`data/coinbase.py:52`).
- [ ] `Property.total_return` converts rent with `USD{rent_currency}`, which assumes the property is priced in USD, and divides by a zero `purchase_price` (`asset_classes/property.py:51`, `:56`).
