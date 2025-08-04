from init import db


class DepositCertificate(db.Model):
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


class DepositCertificateSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cd_id = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)

    date = db.Column(db.String(35), nullable=False)
    amount = db.Column(db.String(20), nullable=False)
    paid = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "depositCertificateId": self.cd_id,
            "transactionDate": self.date,
            "amount": float(self.amount),
            "paid": self.paid == 1,
        }


"""

    assets = get_asset_store(UserStore.get_user_config(current_user.id))
    for country, assetC in assets.items():
        for asset in assetC:
            logging.info(f"Loaded asset {country} {asset.identifier} of type {type(asset)}")
            if type(asset) == DepositCertificate:
                new_bond = DepositCertificateModel(
                    #id=asset.identifier,
                    user_id=int(current_user.id),
                    name=asset.identifier,
                    capital=str(asset.capital),
                    currency=asset.currency,
                    maturity_date=asset.maturity.strftime(Config.DATE_FORMAT_STRING),
                    rate=str(asset.interest_rate),
                    entity=asset.entity,
                    country=asset.country,
                )
                db.session.add(new_bond)
                db.session.commit()
                for payment in asset.interest_schedule:
                    new_payment = DepositCertificateSchedule(
                        cd_id=new_bond.id,
                        user_id=int(current_user.id),
                        date=payment["date"].strftime(Config.DATE_FORMAT_STRING),
                        amount=str(payment["amount"]),
                        paid=1 if payment["paid"] else 0,
                    )
                    db.session.add(new_payment)
                db.session.commit()"""
