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
- [ ] **Check `/reports/cash_flow` and `POST /assets/accounts` against real data.** In the scratch run both returned 500 because the test data had no exchange rates or cash flow data (`IndexError` in `views/cash_flow.py:62`, `KeyError: 'usd'` in `data/asset_store.py`). They passed auth and reached the handlers, but I didn't compare behavior with the pre-migration Flask code. Verify on a copy of the real database before deploying.
- [ ] **Replace the `sys.argv` check for `--debug`.** `init.py` enables the OpenAPI docs by looking for `--debug` in `sys.argv`, because the app is created before argparse runs. Consider an app factory so there is a single source of truth.
- [ ] **Verify the frontend end to end.** The frontend and `mflow-data` were not touched or tested against the migrated backend. Smoke-test login (cookie), the JWT flow and a few react-admin list pages.
