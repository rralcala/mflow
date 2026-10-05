import unittest
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import patch

from asset_classes.account import Account
from asset_classes.bond import Bond
from asset_classes.instrument import Instrument
from asset_classes.payable import Payable
from asset_classes.property import Property
from asset_classes.recurrent import Recurrent
from views.future_timeline import future_timeline

FX = {"USD": 1.0, "PYG": 7000.0}


def account(identifier="Checking", balance=1000.0, currency="USD", country="US"):
    return Account(country, "Bank", identifier, currency, balance)


def instrument(
    location="Sweep",
    symbol="USD",
    value=1200.0,
    rate=0.0,
    cron="0 0 1 * *",
    capital_rate=0.0,
    target="",
    liquid=True,
):
    return Instrument(
        country="US",
        location=location,
        symbol=symbol,
        price=1.0,
        factor=1.0,
        qty=value,
        estimated_dividend=0.0,
        rate=rate,
        dividend=cron,
        currency="USD",
        acquisition_date=datetime(2020, 1, 1),
        acquisition_price=1.0,
        liquid=liquid,
        capital_rate=capital_rate,
        target_asset_id=target,
    )


def recurrent(
    identifier="Rent",
    amount=-100.0,
    cron="0 0 5 * *",
    target="Checking",
    flow_class="expense",
    currency="USD",
    country="US",
    start=datetime(2020, 1, 1),
    end=datetime(2075, 1, 1),
):
    return Recurrent(
        identifier=identifier,
        parent_asset_id="",
        country=country,
        amount=amount,
        currency=currency,
        recurrence=cron,
        start=start,
        end=end,
        flow_class=flow_class,
        target_asset_id=target,
    )


def house(identifier="House-1", price=100000.0, details="", country="PY"):
    return Property(
        country=country,
        currency="USD",
        identifier=identifier,
        purchase_price=price,
        purchase_date=date(2020, 1, 1),
        latest_price=price,
        rented_price=0.0,
        rent_currency="USD",
        additional_data=details,
    )


def run(assets, start=date(2030, 1, 1), end=date(2030, 12, 31), **kwargs):
    return future_timeline(
        {"USD": assets}, end_date=end, start_date=start, fx_rates=FX, **kwargs
    )


def month(result, month_id):
    return next(r for r in result["months"] if r["id"] == month_id)


def asset_row(result, asset_id):
    return next(a for a in result["assets"] if a["id"] == asset_id)


def pool_row(result, pool_id):
    return next(p for p in result["pools"] if p["id"] == pool_id)


@patch.object(Recurrent, "fetch_transactions", return_value=[])
@patch.object(Recurrent, "get_current_value", return_value=(0.0, "USD"))
class TestFutureTimeline(unittest.TestCase):
    def test_runs_monthly_until_end_date(self, *_):
        result = run([account()], end=date(2075, 8, 1))
        self.assertEqual(result["months"][0]["id"], "2030-01")
        self.assertEqual(result["months"][-1]["id"], "2075-08")
        self.assertEqual(result["summary"]["months"], len(result["months"]))

    def test_recurrent_expense_draws_from_target_and_inflates(self, *_):
        result = run([account(), recurrent()], end=date(2031, 1, 31))
        self.assertAlmostEqual(month(result, "2030-01")["balances"]["Checking"], 900.0)
        self.assertAlmostEqual(month(result, "2030-01")["expenses"], -100.0)
        # Twelve months later the expense grew by one year of US inflation.
        self.assertAlmostEqual(month(result, "2031-01")["expenses"], -102.5)

    def test_loans_are_not_inflated_and_pay_down_the_liability(self, *_):
        loan = recurrent(
            "Mortgage", -100.0, flow_class="loan", end=datetime(2031, 1, 31)
        )
        with patch.object(
            Recurrent, "get_current_value", return_value=(-1300.0, "USD")
        ):
            result = run([account(), loan], end=date(2031, 1, 31))
        self.assertAlmostEqual(month(result, "2031-01")["expenses"], -100.0)
        self.assertAlmostEqual(asset_row(result, "Mortgage")["endValue"], 0.0)
        # Paying a loan moves cash into the liability, net worth is unchanged.
        self.assertAlmostEqual(
            result["summary"]["endNetWorth"], result["summary"]["startNetWorth"]
        )

    def test_current_month_discounts_recorded_transactions(self, fetch_value, fetch_tx):
        fetch_tx.return_value = [SimpleNamespace(amount="-100")]
        result = run([account(), recurrent()], end=date(2030, 1, 31))
        self.assertAlmostEqual(month(result, "2030-01")["expenses"], 0.0)
        self.assertAlmostEqual(month(result, "2030-01")["balances"]["Checking"], 1000.0)

    def test_instrument_interest_compounds_into_itself(self, *_):
        sweep = instrument(value=1200.0, rate=0.12)
        result = run([sweep], end=date(2030, 2, 28))
        self.assertAlmostEqual(month(result, "2030-01")["interest"], 12.0)
        self.assertAlmostEqual(month(result, "2030-02")["interest"], 12.12)
        self.assertAlmostEqual(asset_row(result, "Sweep_USD")["endValue"], 1224.12)

    def test_instrument_dividends_go_to_target_account(self, *_):
        stock = instrument(
            "Broker", "VOO", 10000.0, 0.04, "0 0 1 1,4,7,10 *", target="Checking"
        )
        result = run([account(), stock], end=date(2030, 4, 30))
        self.assertAlmostEqual(month(result, "2030-04")["balances"]["Checking"], 1200.0)
        self.assertNotIn("Broker_VOO", month(result, "2030-04")["balances"])

    def test_capital_growth_is_opt_in(self, *_):
        stock = instrument("Broker", "VOO", 1000.0, capital_rate=0.12)
        grown = run([stock], end=date(2030, 12, 31), include_capital_growth=True)
        flat = run([stock], end=date(2030, 12, 31))
        self.assertAlmostEqual(asset_row(grown, "Broker_VOO")["endValue"], 1120.0)
        self.assertAlmostEqual(asset_row(flat, "Broker_VOO")["endValue"], 1000.0)

    def test_bond_coupons_and_maturity_go_to_target(self, *_):
        bond = Bond(
            "BOND-1", 5000.0, 0.06, datetime(2030, 6, 15), "USD", "US", "X", "Checking"
        )
        bond.payment_schedule = [
            {"date": datetime(2029, 12, 15), "amount": 150.0, "paid": True},
            {"date": datetime(2030, 3, 15), "amount": 150.0, "paid": False},
            {"date": datetime(2030, 6, 15), "amount": 150.0, "paid": False},
        ]
        result = run([account(), bond], end=date(2030, 12, 31))
        self.assertAlmostEqual(month(result, "2030-03")["interest"], 150.0)
        self.assertAlmostEqual(month(result, "2030-06")["maturities"], 5000.0)
        self.assertAlmostEqual(month(result, "2030-06")["balances"]["Checking"], 6300.0)
        self.assertAlmostEqual(asset_row(result, "BOND-1")["endValue"], 0.0)
        self.assertAlmostEqual(result["summary"]["endNetWorth"], 6300.0)

    def test_housing_follows_inflation_but_vehicles_do_not(self, *_):
        car = house("Auto-Frontier", 20000.0, "Brand=Nissan,\nVIN=123")
        result = run([house(), car])
        self.assertAlmostEqual(asset_row(result, "House-1")["endValue"], 103500.0)
        self.assertEqual(asset_row(result, "House-1")["growth"], "inflation")
        self.assertAlmostEqual(asset_row(result, "Auto-Frontier")["endValue"], 20000.0)

    def test_inflation_rates_can_be_overridden_per_country(self, *_):
        result = run([house()], inflation_rates={"PY": 0.10})
        self.assertAlmostEqual(asset_row(result, "House-1")["endValue"], 110000.0)
        self.assertEqual(result["inflationRates"]["US"], 0.025)

    def test_foreign_currency_flows_are_converted_into_target(self, *_):
        pyg_expense = recurrent("Gastos", -700000.0, currency="PYG", country="PY")
        result = run([account(), pyg_expense], end=date(2030, 1, 31))
        self.assertAlmostEqual(month(result, "2030-01")["balances"]["Checking"], 900.0)

    def test_detects_negative_balances_within_the_month(self, *_):
        salary = recurrent("Salary", 500.0, "0 0 20 * *", flow_class="income")
        rent = recurrent("Rent", -600.0, "0 0 5 * *")
        result = run([account(balance=200.0), salary, rent], end=date(2030, 3, 31))
        pool = pool_row(result, "Checking")
        # Month-end balance stays positive in January, but the 5th dips below zero.
        self.assertAlmostEqual(month(result, "2030-01")["balances"]["Checking"], 100.0)
        self.assertEqual(month(result, "2030-01")["negativePools"], ["Checking"])
        self.assertEqual(pool["firstNegativeDate"], "2030-01-01")
        self.assertGreater(pool["requiredTopUp"], 0.0)
        self.assertFalse(result["summary"]["onTrack"])

    def test_unknown_target_uses_fallback_pool_and_warns(self, *_):
        result = run([recurrent(target="Missing")], end=date(2030, 1, 31))
        pool = pool_row(result, "Unassigned USD US")
        self.assertTrue(pool["isFallback"])
        self.assertAlmostEqual(pool["endBalance"], -100.0)
        self.assertIn("Rent targets unknown asset 'Missing'.", result["warnings"])

    def test_regular_payable_repeats_yearly_with_inflation(self, *_):
        tuition = Payable(
            "US",
            "USD",
            "Tuition",
            -1000.0,
            -1000.0,
            datetime(2030, 7, 7),
            True,
            False,
            "expense",
            "Checking",
        )
        result = run([account(balance=5000.0), tuition], end=date(2031, 12, 31))
        self.assertAlmostEqual(asset_row(result, "Tuition")["startValue"], -1000.0)
        self.assertAlmostEqual(month(result, "2030-07")["expenses"], -1000.0)
        # Amounts are in today's money, inflated 18 months from the start.
        self.assertAlmostEqual(
            month(result, "2031-07")["expenses"], -1000.0 * 1.025**1.5
        )
        self.assertAlmostEqual(asset_row(result, "Tuition")["endValue"], 0.0)

    def test_one_off_payable_happens_once(self, *_):
        fee = Payable(
            "US",
            "USD",
            "Fee",
            -1000.0,
            -1000.0,
            datetime(2030, 7, 7),
            True,
            True,
            "expense",
            "Checking",
        )
        result = run([account(balance=5000.0), fee], end=date(2031, 12, 31))
        self.assertAlmostEqual(month(result, "2030-07")["expenses"], -1000.0)
        self.assertAlmostEqual(month(result, "2031-07")["expenses"], 0.0)
        self.assertAlmostEqual(month(result, "2031-12")["balances"]["Checking"], 4000.0)

    def test_regular_loan_payable_is_not_inflated(self, *_):
        installment = Payable(
            "US",
            "USD",
            "Installment",
            -1000.0,
            -1000.0,
            datetime(2030, 7, 7),
            False,
            False,
            "Loan",
            "Checking",
        )
        result = run([account(balance=5000.0), installment], end=date(2031, 12, 31))
        self.assertAlmostEqual(month(result, "2031-07")["expenses"], -1000.0)

    def test_overdue_payable_lands_in_first_month(self, *_):
        bill = Payable(
            "US",
            "USD",
            "Bill",
            -50.0,
            -50.0,
            datetime(2029, 11, 1),
            False,
            False,
            "expense",
            "Checking",
        )
        result = run([account(), bill], end=date(2030, 2, 28))
        self.assertAlmostEqual(month(result, "2030-01")["expenses"], -50.0)

    def test_end_before_start_is_rejected(self, *_):
        with self.assertRaises(ValueError):
            run([account()], end=date(2029, 1, 1))


if __name__ == "__main__":
    unittest.main()
