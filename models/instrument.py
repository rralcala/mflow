from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, mapped_column

from data.base import Base
from data.exchange_rates import ExchangeRates


class Instrument(Base):
    __tablename__ = "instrument"

    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(Integer, nullable=False)
    country = mapped_column(String(2), nullable=False)
    location = mapped_column(String(80), nullable=False)
    symbol = mapped_column(String(80), nullable=False)
    factor = mapped_column(String(80), nullable=False)
    qty = mapped_column(String(80), nullable=False)
    dividend = mapped_column(String(80), nullable=False)
    dividend_rate = mapped_column(String(80), nullable=False)
    currency = mapped_column(String(3), nullable=False)
    acquisition_date = mapped_column(String(35), nullable=False)
    acquisition_price = mapped_column(String(80), nullable=False)
    liquid = mapped_column(Integer, nullable=False)
    capital_rate = mapped_column(String(80), nullable=False)

    def __str__(self):
        return str(self.id)

    def to_dict(self):
        value = (
            float(self.qty)
            * float(self.factor)
            * ExchangeRates.exchange_rate(self.symbol)
        )
        monthly_dividend = value * float(self.dividend_rate) / 12
        return {
            "id": self.id,
            "country": self.country,
            "location": self.location,
            "symbol": self.symbol,
            "factor": float(self.factor),
            "qty": float(self.qty),
            "value": value,
            "dividend": self.dividend,
            "dividend_rate": float(self.dividend_rate),
            "estimated_dividend": monthly_dividend,
            "currency": self.currency,
            "acquisition_date": self.acquisition_date,
            "acquisition_price": float(self.acquisition_price),
            "liquid": self.liquid == 1,
            "capital_rate": float(self.capital_rate),
        }
