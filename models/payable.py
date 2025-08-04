from init import db


class Payable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    country = db.Column(db.String(2), nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.String(80), nullable=False)
    due_date = db.Column(db.String(20), nullable=False)
    commited = db.Column(db.Integer, nullable=False)
    balance = db.Column(db.String(80), nullable=True)
    one_off = db.Column(db.Integer, nullable=False, default=0)
    flow_class = db.Column(db.String(20), nullable=True)

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


"""   
def migrate_payables():
    
    assets = get_asset_store(UserStore.get_user_config(current_user.id))
    for country, assetC in assets.items():
        for asset in assetC:
            logging.info(f"Loaded asset {country} {asset.identifier} of type {type(asset)}")
            if type(asset) == PayableAsset:
                new_payable = Payable(
                    user_id=int(current_user.id),
                    country=asset.country,
                    currency=asset.currency,
                    description=asset.identifier,
                    amount=f"{asset.amount:.2f}",
                    due_date=asset.due_date.strftime(Config.DATE_FORMAT_STRING),
                    commited=1 if asset.commited else 0,
                )
                db.session.add(new_payable)
                db.session.commit()
"""
