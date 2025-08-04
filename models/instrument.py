from data.exchange_rates import ExchangeRates
from init import db


class Instrument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    country = db.Column(db.String(2), nullable=False)
    location = db.Column(db.String(80), nullable=False)
    symbol = db.Column(db.String(80), nullable=False)
    factor = db.Column(db.String(80), nullable=False)
    qty = db.Column(db.String(80), nullable=False)
    dividend = db.Column(db.String(80), nullable=False)
    dividend_rate = db.Column(db.String(80), nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    acquisition_date = db.Column(db.String(35), nullable=False)
    acquisition_price = db.Column(db.String(80), nullable=False)
    liquid = db.Column(db.Integer, nullable=False)

    def __str__(self):
        return str(self.id)

    def to_dict(self):
        return {
            "id": self.id,
            "country": self.country,
            "location": self.location,
            "symbol": self.symbol,
            "factor": float(self.factor),
            "qty": float(self.qty),
            "value": float(self.qty)
            * float(self.factor)
            * ExchangeRates.exchange_rate(self.symbol),
            "dividend": self.dividend,
            "dividend_rate": float(self.dividend_rate),
            "estimated_dividend": float(self.qty)
            * float(self.factor)
            * ExchangeRates.exchange_rate(self.symbol)
            * float(self.dividend_rate),
            "currency": self.currency,
            "acquisition_date": self.acquisition_date,
            "acquisition_price": float(self.acquisition_price),
            "liquid": self.liquid == 1,
        }
