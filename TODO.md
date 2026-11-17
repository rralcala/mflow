# TODO

## Planned

- [ ] **Reshape the report payloads.** Replace the shapes that need loose schemas with named fields, together with the dashboards that read them: list rows (`tot_per_location`, `investment_performance` assets, `monthly_pnl` income/expenses, `assets_by_location`, `valuation_history`) as objects; currency-named keys (`monthly_pnl`'s `income_<cur>`, `cash_flow`'s `USD-US` columns) as a list of `{currency, country, amount}` entries; `monthly_pnl` summary arrays `[USD, secondary]` as objects. Then move the three `*_RESPONSE` docs to output schemas.

- [ ] **Migrate login auth to WorkOS (AuthKit).** Replace the password check in `user-<id>/config.json` (`/auth/rlogin`, `/auth/login`, `find_user_by_username`) with WorkOS sign-in, and map each WorkOS user to an mflow user id. Decide what happens to `/auth/jwt` Bearer tokens (keep them for scripts such as the mflow-api skill, or verify WorkOS access tokens instead). The frontend's `authProvider.ts` needs the matching redirect flow. This is also the OAuth server a remote MCP connector would use (dynamic client registration), and it would retire the local password store (`PASSWORD_HASH` in each `user-<id>/config.json`, scrypt-hashed).

## Known bugs

- [ ] **Frontend hardcodes PYG as the secondary currency.** `dashboards/MonthlyPNL.tsx` (`income_PYG` / `expenses_PYG` columns and `USDPYG`), `dashboards/CashFlow.tsx` (`PYG-PY` column), `dashboards/IncomePerLocation.tsx` (header) and `recurrentTransaction.tsx` (totals and `USDPYG`). A user with another `SECONDARY_CURRENCY` gets blank or wrong columns; read it from the payloads (`summary.secondary_currency`, `secondary_currency`) or the profile.

### Low

- [ ] `list_assets` / `list_income` (`nw_summary`, `income_per_location`) divide by the net worth (`views/list_assets.py`), so a user whose assets sum to exactly 0 gets a ZeroDivisionError (500).
- [ ] `GET /reports/nw_summary` writes this month's `History` row as a side effect (`views/list_assets.py`); a read shouldn't write, and the row records whatever the first visit of the month saw.
- [ ] Instrument identifiers join location, account and symbol with `_`, so a location or account containing `_` can collide with another split (`A_B` + `C` vs `A` + `B_C`). Duplicates are still refused, but the clearer fix is to reject `_` in `location` / `account`.
