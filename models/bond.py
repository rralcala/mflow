from init import db


class Bond(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(80), nullable=False)

    capital = db.Column(db.String(20), nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    maturity_date = db.Column(db.String(35), nullable=False)
    rate = db.Column(db.String(10), nullable=False)
    entity = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(2), nullable=False)

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


class BondSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bond_id = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)

    date = db.Column(db.String(35), nullable=False)
    amount = db.Column(db.String(20), nullable=False)
    paid = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "bondId": self.bond_id,
            "transactionDate": self.date,
            "amount": float(self.amount),
            "paid": self.paid == 1,
        }
