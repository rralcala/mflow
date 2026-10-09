# mFlow

Backend for a personal cash flow tracker. It records assets and recurring expenses across institutions and projects net worth and cash flow over a long horizon. The UI lives in the sibling `mflow-frontend` project.

## Features

- Track investments, accounts, property, bonds and certificates of deposit.
- Track one-off and yearly payables, and recurring income and expenses (cron-style schedules).
- Fetch quotes for stocks, metals and crypto (yfinance, Coinbase) and convert between currencies.
- Build a long-term cash flow estimate (see `GET /future_timeline`).

## Requirements

- Python 3.14 (matches the Dockerfile; recent 3.x versions should also work)
- A base directory holding `config.json`, the SQLite database and one folder per user

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt   # use requirements.txt for runtime only
```

### Data directory

The server reads everything from a base directory. `sample-base-dir/` shows the expected layout:

```
<base>/
  config.json            # global config: SECRET_KEY, users, COUNTRIES (required list of allowed country codes), currencies, traded symbols
  mydatabase.db          # SQLite database (schema in sample-base-dir/sqlite-db-schema.sql)
  user-<id>/config.json  # per-user config (Coinbase keys, target estate, default currency, ...)
```

Copy `sample-base-dir/config.sample.json` to `<base>/config.json` and set a real secret and SHA-256 password hashes. Keep this directory out of version control.

## Run

```bash
python service.py --base /path/to/base/   # serves on http://0.0.0.0:5001
```

Docker (the image expects the base directory mounted at `/data`):

```bash
docker build -t mflow .
docker run -p 5001:5001 -v /path/to/base:/data mflow
```

Delete cached quotes with `./clear_cache.sh` when prices look stale.

## Test and format

```bash
python -m unittest -v ./test/*_test.py   # all tests
python -m unittest -v test.util_test     # one module
pre-commit install                       # runs black on commit
```

## API

All routes are served under `/api`. Authenticate with `/api/auth/jwt` and pass the token as a Bearer header. List endpoints support json-server style `_start`/`_end` pagination.

Main resources: `accounts`, `instruments`, `properties`, `payables`, `recurrents`, `monthlyTransactions`, and the aggregate `assets`.

### Reports

Reports are REST resources backed by projection logic in `views/`.

`GET /future_timeline` returns future timeline points for asset value, projected yield and expiration events.

| Param | Values | Default |
|---|---|---|
| `mode` | `flat` or `aggregated` | |
| `granularity` | `monthly` or `yearly` | |
| `startDate`, `endDate` | `YYYY-MM-DD` | optional |
| `includeNonExpiringValue` | `true`/`false` | `true` |
| `includeExpirations` | `true`/`false` | `true` |
| `includeYield` | `true`/`false` | `true` |
| `fallbackYears` | N, used when no asset expires | `5` |
| `_start`, `_end` | pagination | |

```
GET /future_timeline?mode=flat&granularity=monthly
GET /future_timeline?mode=aggregated&granularity=yearly&startDate=2026-01-01
GET /future_timeline?mode=flat&granularity=yearly&_start=0&_end=200
```

### Bulk bond schedule upload

Get a token from:
```
/api/auth/jwt 
```
Then call the following with that token as a Bearer header:
```
/api/assets/bondSchedulesUpload
```
Send CSV-style rows (`iid` is the certificate id; `paid` is 0 or 1):
```
date,amount,paid,iid
2027-10-19,526.68,0,8
2028-01-19,544.44,0,8
2028-04-19,532.60,0,8
2028-07-19,538.52,0,8
2028-10-19,526.68,0,8
2029-01-19,544.44,0,8
2029-04-19,532.60,0,8
2029-07-19,538.52,0,8
2029-10-19,526.68,0,8
2030-01-19,544.44,0,8
2030-04-19,532.60,0,8
2030-07-19,538.52,0,8
```