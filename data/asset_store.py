from datetime import datetime
from typing import Dict, List

from flask_login import current_user

from asset_classes import account, recurrent
from asset_classes.asset import Asset
from asset_classes.bond import Bond
from asset_classes.cd import DepositCertificate
from asset_classes.instrument import Instrument
from asset_classes.payable import Payable
from asset_classes.property import Property
from data.coinbase import fetch_cb_assets
from data.exchange_rates import ExchangeRates
from lib.config import Config
from lib.logger import get_logger
from lib.user_config import UserConfig
from lib.util import count_cron_runs
from models.bond import Bond as BondModel
from models.bond import BondSchedule as BondScheduleModel
from models.deposit_certificate import DepositCertificate as DepositCertificateModel
from models.deposit_certificate import DepositCertificateSchedule
from models.instrument import Instrument as InstrumentModel
from models.models import Account, Recurrent
from models.payable import Payable as PayableModel
from models.property import Property as PropertyModel

logger = get_logger()


def reload_asset_store(user_config: UserConfig) -> Dict[str, List[Asset]]:
    user_config.ASSETS = load_assets(user_config)
    return user_config.ASSETS


def get_asset_store(user_config: UserConfig) -> Dict[str, List[Asset]]:
    if not user_config.ASSETS:
        user_config.ASSETS = reload_asset_store(user_config)
    return user_config.ASSETS


# Add a loader lock.
def load_assets(user_config: UserConfig) -> Dict[str, List[Asset]]:
    with Config.DB_SESSION() as session:
        logger.info("Loading assets from sheets and database")
        assets = {"USD": [], user_config.SECONDARY_CURRENCY: []}
        if user_config.COINBASE_API_KEY and len(user_config.COINBASE_API_KEY) > 0:
            assets["USD"] += fetch_cb_assets(
                user_config.COINBASE_API_KEY,
                user_config.COINBASE_API_SECRET,
                user_config.COINBASE_PORTFOLIO_ID,
                user_config.CRYPTO_RATES,
            )
        try:
            for row in (
                session.query(BondModel).filter_by(user_id=int(current_user.id)).all()
            ):
                asset = Bond(
                    identifier=str(row.name),
                    capital=float(row.capital),
                    interest_rate=float(row.rate),
                    maturity_date=datetime.strptime(
                        row.maturity_date, Config.DATE_FORMAT_STRING
                    ),
                    currency=str(row.currency),
                    country=str(row.country),
                    entity=str(row.entity),
                )
                for irow in (
                    session.query(BondScheduleModel)
                    .filter_by(user_id=int(current_user.id), bond_id=row.id)
                    .all()
                ):
                    payment = {
                        "date": datetime.strptime(irow.date, Config.DATE_FORMAT_STRING),
                        "amount": float(irow.amount),
                        "paid": irow.paid == 1,
                    }
                    asset.payment_schedule.append(payment)
                assets[asset.currency].append(asset)
        except KeyError as e:
            logger.error(f"Present Keys {assets.keys()} - Error loading bonds: {e}")
            raise e

        for row in (
            session.query(DepositCertificateModel)
            .filter_by(user_id=int(current_user.id))
            .all()
        ):
            asset = DepositCertificate(
                identifier=str(row.name),
                capital=float(row.capital),
                maturity_date=datetime.strptime(
                    row.maturity_date, Config.DATE_FORMAT_STRING
                ),
                interest_rate=float(row.rate),
                currency=str(row.currency),
                country=str(row.country),
                entity=str(row.entity),
            )
            for irow in (
                session.query(DepositCertificateSchedule)
                .filter_by(user_id=int(current_user.id), cd_id=row.id)
                .all()
            ):
                payment = {
                    "date": datetime.strptime(irow.date, Config.DATE_FORMAT_STRING),
                    "amount": float(irow.amount),
                    "paid": irow.paid == 1,
                }
                asset.payment_schedule.append(payment)
            assets[asset.currency].append(asset)

        for row in (
            session.query(Recurrent).filter_by(user_id=int(current_user.id)).all()
        ):
            asset = recurrent.Recurrent(
                identifier=str(row.identifier),
                parent_asset_id=str(row.parent_asset_id),
                country=row.country,
                amount=float(row.amount),
                currency=str(row.currency),
                recurrence=row.recurrence,
                start=datetime.strptime(row.start, Config.DATE_FORMAT_STRING),
                end=datetime.strptime(row.end, Config.DATE_FORMAT_STRING),
                flow_class=row.flow_class,
                rate=float(row.rate),
            )

            assets[asset.currency].append(asset)

        for row in (
            session.query(InstrumentModel).filter_by(user_id=int(current_user.id)).all()
        ):
            qty = float(row.qty)
            price = ExchangeRates.exchange_rate(row.symbol)
            rate = float(row.dividend_rate)

            estimated_dividend = 0.0
            if len(row.dividend) > 5:
                year = datetime.now().year
                payouts = count_cron_runs(
                    row.dividend, datetime(year, 1, 1), datetime(year, 12, 31)
                )
                estimated_dividend = qty * price * rate / payouts

            asset = Instrument(
                country=row.country,
                location=row.location,
                symbol=row.symbol,
                factor=float(row.factor),
                price=price,
                qty=qty,
                dividend=row.dividend,
                estimated_dividend=estimated_dividend,
                rate=rate,
                currency=row.currency,
                acquisition_date=datetime.strptime(
                    row.acquisition_date, Config.DATE_FORMAT_STRING
                ),
                acquisition_price=float(row.acquisition_price),
                liquid=row.liquid == 1,
            )
            assets[asset.currency].append(asset)
        for row in session.query(Account).filter_by(user_id=int(current_user.id)).all():
            asset = account.Account(
                identifier=str(row.id),
                country=row.country,
                institution=row.institution,
                currency=row.currency,
                balance=float(row.balance),
                factor=float(row.factor),
                account_type=row.account_type,
                liquid=row.liquid == 1,
            )
            assets[asset.currency].append(asset)
        for row in (
            session.query(PayableModel).filter_by(user_id=int(current_user.id)).all()
        ):
            asset = Payable(
                identifier=row.description,
                country=row.country,
                currency=row.currency,
                amount=float(row.amount),
                due_date=datetime.strptime(row.due_date, Config.DATE_FORMAT_STRING),
                commited=row.commited == 1,
                balance=float(row.balance),
                one_off=row.one_off == 1,
                flow_class=row.flow_class,
            )
            assets[asset.currency].append(asset)
        for row in (
            session.query(PropertyModel).filter_by(user_id=int(current_user.id)).all()
        ):
            asset = Property(
                identifier=row.property_name,
                country=row.country,
                currency=row.currency,
                purchase_price=float(row.purchase_price),
                purchase_date=datetime.strptime(
                    row.purchase_date, Config.DATE_FORMAT_STRING
                ).date(),
                latest_price=float(row.current_price),
                rented_price=float(row.rent_price),
                additional_data=row.additional_data,
                rent_currency=row.rent_currency,
            )
            assets[asset.currency].append(asset)
        return assets
