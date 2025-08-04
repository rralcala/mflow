from init import db


class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    date = db.Column(db.String(20), nullable=False)
    value = db.Column(db.String(80), nullable=False)
    fixed = db.Column(db.String(80), nullable=False)

    def __str__(self):
        return str(self.date) + " - " + str(self.value)

    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date,
            "value": float(self.value),
            "fixed": float(self.fixed),
        }
