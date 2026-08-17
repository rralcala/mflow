# mFlow:

### What it does

- Manage Investments across institutions.
- Track Income and Payments.
- Track Budgets "Recurrents"
- And more...

You'll also need *mflow-frontend* to interact with the api.

### Install:

```
python -m venv .venv
Activate venv
pip install -r requirements.txt
python service.py /data_and_config_dir/
```
### Test:

```
python -m unittest -v ./test/*_test.py
```
### Reports API:

Reports are exposed as REST resources and backed by projection logic under views/.

GET /future_timeline
- Purpose: return future timeline points for asset value, projected yield amount and expiration events.
- Query params:
	- mode=flat|aggregated
	- granularity=monthly|yearly
	- startDate=YYYY-MM-DD (optional)
	- endDate=YYYY-MM-DD (optional)
	- includeNonExpiringValue=true|false (default true)
	- includeExpirations=true|false (default true)
	- includeYield=true|false (default true)
	- fallbackYears=N (default 5, used when no asset expiration exists)
	- _start, _end for pagination

Example calls:

GET /future_timeline?mode=flat&granularity=monthly
GET /future_timeline?mode=aggregated&granularity=yearly&startDate=2026-01-01
GET /future_timeline?mode=flat&granularity=yearly&_start=0&_end=200

### Multi row interest creation
Grab a token from:
```
/api/auth/jwt 
```
And use it as bearer token to call:
```
/api/assets/bondSchedulesUpload
```
With the following data, csv like rows where iid is the certificate id:
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