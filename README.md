What it does:
Manage Investments across institutions.
Track Income and Payments.
Track Budgets "Recurrents"

Install:

python -m venv .venv
Activate venv
pip install -r requirements.txt
python service.py /data_and_config_dir/

Test:

python -m unittest -v ./test/*_test.py

Reports API:

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
