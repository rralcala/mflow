from sqlalchemy import Integer, String
from sqlalchemy.orm import mapped_column

from data.base import Base


class Property(Base):
    __tablename__ = "property"

    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(Integer, nullable=False)
    property_name = mapped_column(String(255), nullable=False)
    country = mapped_column(String(2), nullable=False)
    currency = mapped_column(String(3), nullable=False)
    purchase_price = mapped_column(String(80), nullable=False)
    purchase_date = mapped_column(String(20), nullable=False)
    current_price = mapped_column(String(80), nullable=False)
    rent_price = mapped_column(String(80), nullable=False)
    depreciation = mapped_column(String(10), nullable=False)
    additional_data = mapped_column(String(255), nullable=False)
    rent_currency = mapped_column(String(3), nullable=False)

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
