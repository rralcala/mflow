from init import db


class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    property_name = db.Column(db.String(255), nullable=False)
    country = db.Column(db.String(2), nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    purchase_price = db.Column(db.String(80), nullable=False)
    purchase_date = db.Column(db.String(20), nullable=False)
    current_price = db.Column(db.String(80), nullable=False)
    rent_price = db.Column(db.String(80), nullable=False)
    depreciation = db.Column(db.String(10), nullable=False)
    additional_data = db.Column(db.String(255), nullable=False)
    rent_currency = db.Column(db.String(3), nullable=False)

    def __str__(self):
        return self.property_name

    def to_dict(self):
        return {
            "id": self.id,
            "country": self.country,
            "currency": self.currency,
            "propertyName": self.property_name,
            "purchasePrice": float(self.purchase_price),
            "purchaseDate": self.purchase_date,
            "currentPrice": float(self.current_price),
            "rentPrice": float(self.rent_price),
            "depreciation": float(self.depreciation),
            "additionalData": self.additional_data,
            "rentCurrency": self.rent_currency,
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
                    property_name=asset.identifier,
                    purchase_price=f"{asset.amount:.2f}",
                    purchase_date=asset.due_date.strftime(Config.DATE_FORMAT_STRING),
                    current_price=f"{asset.current_price:.2f}",
                    rent_price=f"{asset.rent_price:.2f}",
                    depreciation=f"{asset.depreciation:.2f}",
                    additional_data=asset.additional_data,
                    rent_currency=asset.rent_currency,
                )
                db.session.add(new_payable)
                db.session.commit()
"""
