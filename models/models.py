from flask_login import UserMixin
from sqlalchemy import Integer, String
from sqlalchemy.orm import mapped_column

from data.base import Base
from lib.config import Config
from lib.logger import get_logger
from lib.util import get_formatted_date, sha256_hash

logger = get_logger()


class Account(Base):
    __tablename__ = "account"

    id = mapped_column(String(80), primary_key=True)
    country = mapped_column(String(2), nullable=True)
    institution = mapped_column(String(80), nullable=False)
    currency = mapped_column(String(3), nullable=False)
    balance = mapped_column(String(20), nullable=False)
    factor = mapped_column(String(20), nullable=False)
    account_type = mapped_column(String(35), nullable=False)
    liquid = mapped_column(Integer(), nullable=False)
    user_id = mapped_column(Integer, nullable=False)

    def __str__(self):
        return self.id

    def to_dict(self):
        return {
            "id": self.id,
            "country": self.country,
            "institution": self.institution,
            "currency": self.currency,
            "balance": float(self.balance),
            "factor": float(self.factor),
            "accountType": self.account_type,
            "liquid": self.liquid == 1,
        }


class Recurrent(Base):
    __tablename__ = "recurrent"

    identifier = mapped_column(String(80), primary_key=True)
    parent_asset_id = mapped_column(String(80), nullable=True)
    country = mapped_column(String(2), nullable=False)
    amount = mapped_column(String(20), nullable=False)
    currency = mapped_column(String(3), nullable=False)
    recurrence = mapped_column(String(20), nullable=False)
    start = mapped_column(String(35), nullable=False)
    end = mapped_column(String(35), nullable=False)
    flow_class = mapped_column(String(20), nullable=False)
    rate = mapped_column(String(20), nullable=False)
    user_id = mapped_column(Integer, nullable=False)

    def __str__(self):
        return self.identifier

    def to_dict(self):
        return {
            "id": self.identifier,
            "assetId": self.parent_asset_id,
            "country": self.country,
            "amount": float(self.amount),
            "currency": self.currency,
            "recurrence": self.recurrence,
            "start": self.start,
            "end": self.end,
            "flowClass": self.flow_class,
            "rate": float(self.rate),
        }


class RecurrentTransaction(Base):
    __tablename__ = "recurrent_transaction"

    transaction_id = mapped_column(Integer, primary_key=True)
    parent_id = mapped_column(String(80), nullable=False)
    year_month = mapped_column(String(7), nullable=False)
    description = mapped_column(String(200), nullable=False)
    amount = mapped_column(String(20), nullable=False)
    transaction_date = mapped_column(String(35), nullable=False)
    paid_with = mapped_column(String(80), nullable=False)
    create_date = mapped_column(String(35), nullable=False, default=get_formatted_date)
    user_id = mapped_column(Integer, nullable=False)

    def to_dict(self):
        return {
            "id": self.transaction_id,
            "recurrentId": self.parent_id,
            "yearMonth": self.year_month,
            "description": self.description,
            "amount": float(self.amount),
            "transactionDate": self.transaction_date,
            "paidWithAssetId": self.paid_with,
            "createDate": self.create_date,
        }


class User(UserMixin):
    def __init__(self, uid, username, name, password, email):
        self.id = uid
        self.username = username
        self.name = name
        self.password = password
        self.email = email

    def set_password(self, password):
        self.password = sha256_hash(password)

    def check_password(self, password):
        hashed_password = sha256_hash(password)
        logger.warning(
            f"Checking password for user {self.username} {self.password} against {hashed_password}"
        )
        return self.password == hashed_password


def find_user_by_username(username):
    for uid, user_data in Config.USERS.items():
        if user_data.get("username") == username:
            return User(
                uid=uid,
                username=user_data.get("username"),
                name=user_data.get("name"),
                password=user_data.get("password"),
                email=user_data.get("email"),
            )
    return None
