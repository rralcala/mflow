"""Deletes and renames that would leave other assets dangling are refused, and
child rows can only be attached to parents the caller owns."""

import unittest
from http import HTTPStatus
from test.rest_assets_test import api_app, run_view
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from data.base import Base
from lib.config import Config
from models.bond import Bond, BondSchedule
from models.deposit_certificate import DepositCertificate, DepositCertificateSchedule
from models.instrument import Instrument
from models.models import Account, Recurrent, RecurrentTransaction
from models.payable import Payable
from models.property import Property
from routes.assets import rest_assets, rest_certificates, rest_recurrents

TABLES = [
    Account,
    Bond,
    BondSchedule,
    DepositCertificate,
    DepositCertificateSchedule,
    Instrument,
    Payable,
    Property,
    Recurrent,
    RecurrentTransaction,
]


def account(id, user_id=1, **kw):
    return Account(
        id=id,
        country="US",
        institution="Bank",
        currency="USD",
        balance="100",
        factor="1",
        account_type="checking",
        liquid=1,
        user_id=user_id,
        **kw,
    )


def instrument(id, location, symbol, user_id=1, **kw):
    return Instrument(
        id=id,
        user_id=user_id,
        country="US",
        location=location,
        symbol=symbol,
        factor="1",
        qty="1",
        dividend="N",
        dividend_rate="0",
        currency="USD",
        acquisition_date="2026-01-01",
        acquisition_price="1",
        liquid=1,
        capital_rate="0",
        **kw,
    )


def recurrent(identifier, user_id=1, **kw):
    return Recurrent(
        identifier=identifier,
        country="US",
        amount="-100",
        currency="USD",
        recurrence="0 0 1 * *",
        start="2026-01-01",
        end="2030-01-01",
        flow_class="expense",
        rate="0",
        user_id=user_id,
        **kw,
    )


def certificate(model, id, name, user_id=1):
    return model(
        id=id,
        user_id=user_id,
        name=name,
        capital="1000",
        currency="USD",
        maturity_date="2030-01-01",
        rate="0.05",
        entity="Bank",
        country="US",
        purchase_price="1000",
        target_asset_id="Checking",
    )


class TestDanglingReferences(unittest.TestCase):
    def setUp(self):
        self.app = api_app()
        engine = create_engine("sqlite://")
        self.addCleanup(engine.dispose)
        Base.metadata.create_all(engine, tables=[t.__table__ for t in TABLES])
        self.Session = sessionmaker(bind=engine)
        with self.Session() as session:
            session.add_all(
                [
                    account("Checking"),
                    account("Spare"),
                    instrument(1, "Puente", "USD", is_target_pool=1),
                    instrument(2, "Citi", "VOO"),
                    Property(
                        id=1,
                        user_id=1,
                        property_name="House",
                        country="US",
                        currency="USD",
                        purchase_price="1000",
                        purchase_date="2020-01-01",
                        current_price="1000",
                        rent_price="0",
                        depreciation="0",
                        additional_data="",
                        rent_currency="USD",
                    ),
                    Payable(
                        id=1,
                        user_id=1,
                        country="US",
                        currency="USD",
                        description="Car tax",
                        amount="10",
                        due_date="2027-01-01",
                        commited=0,
                        balance="10",
                        target_asset_id="Checking",
                    ),
                    certificate(Bond, 1, "BOND-A"),
                    certificate(Bond, 2, "BOND-THEIRS", user_id=2),
                    certificate(DepositCertificate, 1, "CD-A"),
                    certificate(DepositCertificate, 2, "CD-THEIRS", user_id=2),
                    BondSchedule(
                        id=1,
                        bond_id=1,
                        user_id=1,
                        date="2027-01-01",
                        amount="5",
                        paid=0,
                    ),
                    recurrent(
                        "Rent", target_asset_id="Checking", parent_asset_id="House"
                    ),
                    recurrent("Interest", target_asset_id="Puente_USD"),
                    recurrent("Food", target_asset_id="Checking"),
                    RecurrentTransaction(
                        transaction_id=1,
                        parent_id="Food",
                        year_month="2026-10",
                        description="Groceries",
                        amount="-10",
                        transaction_date="2026-10-08",
                        paid_with="Checking",
                        user_id=1,
                    ),
                ]
            )
            session.commit()
        user = SimpleNamespace(id="1")
        targets = [
            patch.object(Config, "DB_SESSION", self.Session, create=True),
            patch.object(Config, "COUNTRIES", ["US", "PY"], create=True),
            patch.object(Config, "CURRENCIES", ["usd", "pyg"], create=True),
        ]
        for module in (rest_assets, rest_certificates, rest_recurrents):
            targets += [
                patch.object(module, "current_user", user),
                patch.object(module, "reload_asset_store"),
                patch.object(module.UserStore, "get_user_config"),
            ]
        for target in targets:
            target.start()
            self.addCleanup(target.stop)

    def call(self, view, *args, method="DELETE", json=None):
        with self.app.test_request_context("/", method=method, json=json):
            response, status = run_view(view, *args)
        return response.get_json(), status

    def exists(self, model, **filters):
        with self.Session() as session:
            return session.query(model).filter_by(**filters).first() is not None

    # Accounts

    def test_account_delete_refused_while_targeted(self):
        body, status = self.call(rest_assets.account_delete, "Checking")
        self.assertEqual(status, HTTPStatus.CONFLICT)
        self.assertEqual(
            body["message"],
            "Can't delete Checking: still used by BOND-A, CD-A, Car tax, Food, "
            "Rent; retarget or remove them first",
        )
        self.assertTrue(self.exists(Account, id="Checking"))

    def test_unused_account_deletes(self):
        _, status = self.call(rest_assets.account_delete, "Spare")
        self.assertEqual(status, HTTPStatus.OK)
        self.assertFalse(self.exists(Account, id="Spare"))

    def test_account_currency_change_refused_while_targeted(self):
        body, status = self.call(
            rest_assets.account_update,
            "Checking",
            method="PUT",
            json={"currency": "PYG"},
        )
        self.assertEqual(status, HTTPStatus.BAD_REQUEST)
        self.assertIn("Can't change the currency of Checking", body["message"])
        with self.Session() as session:
            self.assertEqual(session.get(Account, "Checking").currency, "USD")

    def test_account_currency_change_allowed_when_unused(self):
        _, status = self.call(
            rest_assets.account_update, "Spare", method="PUT", json={"currency": "PYG"}
        )
        self.assertEqual(status, HTTPStatus.OK)

    # Instruments

    def test_instrument_delete_refused_while_targeted(self):
        body, status = self.call(rest_assets.instrument_delete, 1)
        self.assertEqual(status, HTTPStatus.CONFLICT)
        self.assertIn("still used by Interest", body["message"])
        self.assertTrue(self.exists(Instrument, id=1))

    def test_instrument_rename_refused_while_targeted(self):
        for change in ({"location": "Other"}, {"symbol": "PYG"}):
            with patch.object(
                rest_assets, "instrument_symbol_error", return_value=None
            ):
                body, status = self.call(
                    rest_assets.instrument_update, 1, method="PUT", json=change
                )
            self.assertEqual(status, HTTPStatus.BAD_REQUEST, change)
            self.assertIn("Can't rename Puente_USD", body["message"])

    def test_unused_instrument_deletes(self):
        # The response values the instrument from quotes.
        with patch("models.instrument.ExchangeRates.exchange_rate", return_value=1.0):
            _, status = self.call(rest_assets.instrument_delete, 2)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertFalse(self.exists(Instrument, id=2))

    # Properties and payables

    def test_property_delete_refused_with_attached_recurrent(self):
        body, status = self.call(rest_assets.property_delete, 1)
        self.assertEqual(status, HTTPStatus.CONFLICT)
        self.assertIn("still used by Rent", body["message"])

    def test_property_rename_refused_with_attached_recurrent(self):
        body, status = self.call(
            rest_assets.property_update,
            1,
            method="PUT",
            json={"propertyName": "Home"},
        )
        self.assertEqual(status, HTTPStatus.BAD_REQUEST)
        self.assertIn("Can't rename House", body["message"])

    def test_unused_payable_deletes(self):
        _, status = self.call(rest_assets.payable_delete, 1)
        self.assertEqual(status, HTTPStatus.OK)

    # Bonds and CDs

    def test_bond_delete_refused_while_it_has_schedule_rows(self):
        body, status = self.call(rest_certificates.bond_delete, "1")
        self.assertEqual(status, HTTPStatus.CONFLICT)
        self.assertEqual(
            body["message"],
            "Can't delete BOND-A: it still has 1 scheduled payment(s); "
            "delete them first",
        )
        self.assertTrue(self.exists(Bond, id=1))

    def test_bond_deletes_once_its_schedule_is_gone(self):
        _, status = self.call(rest_certificates.bond_schedule_delete, "1")
        self.assertEqual(status, HTTPStatus.OK)
        _, status = self.call(rest_certificates.bond_delete, "1")
        self.assertEqual(status, HTTPStatus.OK)
        self.assertFalse(self.exists(Bond, id=1))

    def test_cd_without_schedule_deletes(self):
        _, status = self.call(rest_certificates.deposit_certificate_delete, 1)
        self.assertEqual(status, HTTPStatus.OK)

    def test_other_users_schedule_cannot_be_deleted(self):
        with self.Session() as session:
            session.add(
                BondSchedule(
                    id=2, bond_id=2, user_id=2, date="2027-01-01", amount="5", paid=0
                )
            )
            session.commit()
        _, status = self.call(rest_certificates.bond_schedule_delete, "2")
        self.assertEqual(status, HTTPStatus.NOT_FOUND)
        self.assertTrue(self.exists(BondSchedule, id=2))

    def schedule(self, key, parent_id):
        return {key: parent_id, "transactionDate": "2027-06-01", "amount": 5}

    def test_bond_schedule_post_needs_an_owned_bond(self):
        for bond_id in (2, 99):
            body, status = self.call(
                rest_certificates.bond_schedule_create,
                method="POST",
                json=self.schedule("bondId", bond_id),
            )
            self.assertEqual(status, HTTPStatus.NOT_FOUND, bond_id)
            self.assertEqual(body["message"], f"Bond {bond_id} not found")
        _, status = self.call(
            rest_certificates.bond_schedule_create,
            method="POST",
            json=self.schedule("bondId", 1),
        )
        self.assertEqual(status, HTTPStatus.CREATED)

    def test_cd_schedule_post_needs_an_owned_cd(self):
        _, status = self.call(
            rest_certificates.deposit_certificate_schedule_create,
            method="POST",
            json=self.schedule("cdId", 2),
        )
        self.assertEqual(status, HTTPStatus.NOT_FOUND)
        self.assertFalse(self.exists(DepositCertificateSchedule, cd_id=2))
        _, status = self.call(
            rest_certificates.deposit_certificate_schedule_create,
            method="POST",
            json=self.schedule("cdId", 1),
        )
        self.assertEqual(status, HTTPStatus.CREATED)

    # Recurrents

    def test_recurrent_delete_refused_while_it_has_transactions(self):
        body, status = self.call(rest_recurrents.recurrent_delete, "Food")
        self.assertEqual(status, HTTPStatus.CONFLICT)
        self.assertEqual(
            body["message"],
            "Can't delete Food: it still has 1 transaction(s); delete them first",
        )
        self.assertTrue(self.exists(Recurrent, identifier="Food"))

    def test_recurrent_without_transactions_deletes(self):
        _, status = self.call(rest_recurrents.recurrent_delete, "Rent")
        self.assertEqual(status, HTTPStatus.OK)

    def test_recurrent_parent_must_be_an_owned_asset(self):
        body, status = self.call(
            rest_recurrents.recurrent_update,
            "Food",
            method="PUT",
            json={"assetId": "BOND-THEIRS"},
        )
        self.assertEqual(status, HTTPStatus.BAD_REQUEST)
        self.assertEqual(body["message"], "Unknown asset 'BOND-THEIRS'")
        _, status = self.call(
            rest_recurrents.recurrent_update,
            "Food",
            method="PUT",
            json={"assetId": "Citi_VOO"},
        )
        self.assertEqual(status, HTTPStatus.OK)


if __name__ == "__main__":
    unittest.main()
