from sqlalchemy import Integer, String
from sqlalchemy.orm import mapped_column

from data.base import Base


class Quote(Base):
    __tablename__ = "quotes"

    id = mapped_column(Integer, primary_key=True)
    date = mapped_column(String(20), nullable=False)
    symbol = mapped_column(String(80), nullable=False)
    value = mapped_column(String(80), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date,
            "symbol": self.symbol,
            "value": float(self.value),
        }
