from datetime import datetime

from asset_classes.bond import Bond


class DepositCertificate(Bond):
    """Class representing a certificate of deposit (CD) asset."""

    def __init__(
        self,
        identifier: str,
        capital: float,
        interest_rate: float,
        maturity_date: datetime,
        currency: str,
        country: str,
        entity: str,
    ):
        super().__init__(
            identifier=identifier,
            capital=capital,
            interest_rate=interest_rate,
            maturity_date=maturity_date,
            currency=currency,
            country=country,
            entity=entity,
        )
