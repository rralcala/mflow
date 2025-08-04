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
