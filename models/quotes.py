from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import mapped_column

from data.base import Base


class Quote(Base):
    __tablename__ = "quotes"

    id = mapped_column(Integer, primary_key=True)
    date = mapped_column(String(10), nullable=False)
    symbol = mapped_column(String(15), nullable=False)
    value = mapped_column(String(80), nullable=False)

    __table_args__ = (UniqueConstraint("date", "symbol", name="quotes-date-symbol"),)

    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date,
            "symbol": self.symbol,
            "value": float(self.value),
        }
