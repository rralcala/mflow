import logging

from flask_login import UserMixin

from init import db
from lib.config import Config
from lib.util import get_formatted_date, sha256_hash


class Account(db.Model):
    id = db.Column(db.String(80), primary_key=True)
    country = db.Column(db.String(2), nullable=True)
    institution = db.Column(db.String(80), nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    balance = db.Column(db.String(20), nullable=False)
    factor = db.Column(db.String(20), nullable=False)
    account_type = db.Column(db.String(35), nullable=False)
    liquid = db.Column(db.Integer(), nullable=False)
    user_id = db.Column(db.Integer, nullable=False)

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


class Recurrent(db.Model):
    identifier = db.Column(db.String(80), primary_key=True)
    parent_asset_id = db.Column(db.String(80), nullable=True)
    country = db.Column(db.String(2), nullable=False)
    amount = db.Column(db.String(20), nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    recurrence = db.Column(db.String(20), nullable=False)
    start = db.Column(db.String(35), nullable=False)
    end = db.Column(db.String(35), nullable=False)
    flow_class = db.Column(db.String(20), nullable=False)
    rate = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.Integer, nullable=False)

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


class RecurrentTransaction(db.Model):
    transaction_id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.String(80), nullable=False)
    year_month = db.Column(db.String(7), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.String(20), nullable=False)
    transaction_date = db.Column(db.String(35), nullable=False)
    paid_with = db.Column(db.String(80), nullable=False)
    create_date = db.Column(db.String(35), nullable=False, default=get_formatted_date)
    user_id = db.Column(db.Integer, nullable=False)

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
        logging.warning(
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
