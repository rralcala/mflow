# TODO

Follow-ups from the Flask → APIFlask migration.

- [ ] **Add request/response schemas.** Endpoints have no `@app.input` / `@app.output` marshmallow schemas, so the OpenAPI spec lists paths and auth but no body shapes. Add them incrementally, keeping the json-server-style responses (raw lists, `X-Total-Count`) that `ra-data-json-server` expects.
- [ ] **Complete the json-server query conventions (`_start`, `_end`, `_sort`, `_order`) on list endpoints.** Only some list endpoints implement them, each with its own copy-pasted code. Audit of `GET` collection routes:

  | Endpoint | `_sort` / `_order` | `_start` / `_end` | Missing |
  |---|---|---|---|
  | `/accounts`, `/assets`, `/instruments`, `/payables`, `/properties` | yes | yes | none |
  | `/bonds`, `/depositCertificates` (`certificates_all`) | only `name` and `maturityDate` (any other key silently falls back to no ordering) | no | `_start`/`_end`, all other sort keys |
  | `/bondSchedules`, `/depositCertificateSchedules` | no | no | all four |
  | `/recurrents`, `/recurrentTransactions`, `/monthlyTransactions` | no | no | all four |
  | `/exchangeRates` | no | no | all four |
  | `/upcoming_payments` | no | yes | `_sort`, `_order` |
  | Report endpoints (`/cash_flow`, `/assets_by_location`, `/income_per_location`, `/investment_performance`, `/monthly_pnl`, `/nw_summary`, `/projection_analysis`, `/spending_analysis`, `/valuation_history`, `/future_timeline`) | no | no | all four, if the frontend lists them via react-admin (dashboards may not need them) |

  `X-Total-Count` is already set on every collection `GET` (including `/bonds` and `/depositCertificates` via `certificates_all`), so nothing is missing there. It is currently the full count only where `_start`/`_end` is implemented; the endpoints above that gain slicing must keep it as the pre-slice count.

  Extract one shared helper (sort by `_sort`/`_order`, slice by `_start`/`_end`, set `X-Total-Count` to the pre-slice count) and use it everywhere instead of repeating the block. Things to settle: sort keys that are missing or `None` on some rows (the current `x.get(sort_key, "")` can raise on mixed types), `_order` case handling, invalid `_start`/`_end` values (currently `int()` raises a 500), and `X-Total-Count` must be the count before slicing. Add unit tests for the helper and for each endpoint touched.
- [ ] **Document cookie auth as its own security scheme.** The spec only lists `BearerAuth`; cookie support is only mentioned in its description. Add a `CookieAuth` (`apiKey`, `in: cookie`) scheme via `SECURITY_SCHEMES` and reference both on protected operations.
- [ ] **Check `/reports/cash_flow` and `POST /assets/accounts` against real data.** In the scratch run both returned 500 because the test data had no exchange rates or cash flow data (`IndexError` in `views/cash_flow.py:62`, `KeyError: 'usd'` in `data/asset_store.py`). They passed auth and reached the handlers, but I didn't compare behavior with the pre-migration Flask code. Verify on a copy of the real database before deploying.
- [ ] **Replace the `sys.argv` check for `--debug`.** `init.py` enables the OpenAPI docs by looking for `--debug` in `sys.argv`, because the app is created before argparse runs. Consider an app factory so there is a single source of truth.
- [ ] **Verify the frontend end to end.** The frontend and `mflow-data` were not touched or tested against the migrated backend. Smoke-test login (cookie), the JWT flow and a few react-admin list pages.
