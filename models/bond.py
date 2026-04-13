from sqlalchemy import Integer, String
from sqlalchemy.orm import mapped_column

from data.base import Base


class Bond(Base):
    __tablename__ = "bond"

    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(Integer, nullable=False)
    name = mapped_column(String(80), nullable=False)

    capital = mapped_column(String(20), nullable=False)
    currency = mapped_column(String(3), nullable=False)
    maturity_date = mapped_column(String(35), nullable=False)
    rate = mapped_column(String(10), nullable=False)
    entity = mapped_column(String(20), nullable=False)
    country = mapped_column(String(2), nullable=False)

    def __str__(self):
        return str(self.id)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "capital": float(self.capital),
            "currency": self.currency,
            "maturityDate": self.maturity_date,
            "rate": float(self.rate),
            "entity": self.entity,
            "country": self.country,
        }


class BondSchedule(Base):
    __tablename__ = "bond_schedule"

    id = mapped_column(Integer, primary_key=True)
    bond_id = mapped_column(Integer, nullable=False)
    user_id = mapped_column(Integer, nullable=False)

    date = mapped_column(String(35), nullable=False)
    amount = mapped_column(String(20), nullable=False)
    paid = mapped_column(Integer, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "bondId": self.bond_id,
            "transactionDate": self.date,
            "amount": float(self.amount),
            "paid": self.paid == 1,
        }
