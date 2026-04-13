from sqlalchemy import Integer, String
from sqlalchemy.orm import mapped_column

from data.base import Base


class Payable(Base):
    __tablename__ = "payable"

    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(Integer, nullable=False)
    country = mapped_column(String(2), nullable=False)
    currency = mapped_column(String(3), nullable=False)
    description = mapped_column(String(255), nullable=False)
    amount = mapped_column(String(80), nullable=False)
    due_date = mapped_column(String(20), nullable=False)
    commited = mapped_column(Integer, nullable=False)
    balance = mapped_column(String(80), nullable=True)
    one_off = mapped_column(Integer, nullable=False, default=0)
    flow_class = mapped_column(String(20), nullable=True)

    def __str__(self):
        return self.description

    def to_dict(self):
        return {
            "id": self.id,
            "country": self.country,
            "currency": self.currency,
            "description": self.description,
            "amount": float(self.amount),
            "dueDate": self.due_date,
            "commited": self.commited == 1,
            "balance": float(self.balance),
            "oneOff": self.one_off == 1,
            "flowClass": self.flow_class,
        }
