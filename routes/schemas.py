"""Request and response schemas for the REST API.

Input schemas check shape and types: required fields, numbers, dates and
booleans. They drop unknown keys, because react-admin sends whole records back
on update, read-only fields included. Rules that need the user's config or the
database (allowed currencies and countries, target assets, cron patterns) stay
in the routes. A PUT body is the POST schema with partial=True, so a field left
out keeps its stored value.

Output schemas mirror the models' to_dict(); test/schemas_test.py checks that
they stay in step. List endpoints return a raw array plus an X-Total-Count
header, as ra-data-json-server expects.
"""

from apiflask import Schema
from apiflask.fields import (
    Boolean,
    Date,
    Dict,
    File,
    Float,
    Integer,
    List,
    Nested,
    String,
)
from apiflask.validators import Length, Range, Regexp
from marshmallow import EXCLUDE

from lib.parsers.base import YEAR_MONTH


class BlankIsNone:
    """With allow_none, an empty string (a cleared form input) loads as None."""

    def deserialize(self, value, attr=None, data=None, **kwargs):
        if value == "" and self.allow_none:
            value = None
        return super().deserialize(value, attr, data, **kwargs)


class DateString(BlankIsNone, Date):
    """A YYYY-MM-DD date, kept as the string the models store."""

    default_error_messages = {"invalid": "Not a valid date, expected YYYY-MM-DD."}

    def __init__(self, **kwargs):
        super().__init__(format="%Y-%m-%d", **kwargs)

    def _serialize(self, value, attr, obj, **kwargs):
        return value

    def _deserialize(self, value, attr, data, **kwargs):
        super()._deserialize(value, attr, data, **kwargs)
        return value


class YearMonth(BlankIsNone, String):
    """A YYYY-MM month, the key transactions are recorded under."""

    def __init__(self, **kwargs):
        super().__init__(
            validate=Regexp(YEAR_MONTH, error="Not a valid month, expected YYYY-MM."),
            **kwargs,
        )


class In(Schema):
    class Meta:
        unknown = EXCLUDE


# Common


class MessageOut(Schema):
    message = String()


class TotalCountHeader(Schema):
    total = Integer(
        data_key="X-Total-Count",
        metadata={"description": "Number of items before pagination."},
    )


class PageQuery(In):
    """json-server pagination: the slice [_start, _end) of the full list."""

    start = Integer(data_key="_start", validate=Range(min=0))
    end = Integer(data_key="_end", validate=Range(min=0))


class ListQuery(PageQuery):
    sort = String(data_key="_sort", metadata={"description": "Field to sort by."})
    order = String(data_key="_order", metadata={"description": "ASC or DESC."})


# Accounts


class AccountIn(In):
    id = String(required=True)
    country = String(required=True)
    institution = String(required=True)
    currency = String(required=True)
    balance = Float(required=True)
    factor = Float(required=True)
    accountType = String(required=True)
    liquid = Boolean(allow_none=True)
    transferBy = DateString(
        allow_none=True,
        metadata={"description": "Date the balance moves to targetAssetId."},
    )
    targetAssetId = String(allow_none=True)


class AccountOut(Schema):
    id = String()
    country = String()
    institution = String()
    currency = String()
    balance = Float()
    factor = Float()
    accountType = String()
    liquid = Boolean()
    transferBy = DateString()
    targetAssetId = String()


# Assets (every type, as loaded into the asset store)


class AssetsQuery(ListQuery):
    liquid = Boolean(metadata={"description": "Only liquid assets."})
    targetPool = Boolean(metadata={"description": "Only target-pool instruments."})
    id = List(String(), metadata={"description": "Only these ids (repeatable)."})


class AssetOut(Schema):
    id = String()
    currentValue = Float()
    currency = String()
    type = String()
    details = String()
    liquid = Boolean()


# Instruments


class InstrumentIn(In):
    country = String(required=True)
    location = String(required=True)
    symbol = String(required=True)
    currency = String(required=True)
    factor = Float(required=True)
    qty = Float(required=True)
    dividend = String(
        required=True,
        metadata={"description": "N for none, or a cron pattern of payout dates."},
    )
    dividend_rate = Float(required=True)
    acquisition_date = DateString(required=True)
    acquisition_price = Float(required=True)
    liquid = Boolean(allow_none=True)
    capital_rate = Float(metadata={"description": "Defaults to 0."})
    targetAssetId = String(required=True)
    sellBy = DateString(allow_none=True)
    isTargetPool = Boolean(allow_none=True)


class InstrumentOut(Schema):
    id = Integer()
    country = String()
    location = String()
    symbol = String()
    factor = Float()
    qty = Float()
    value = Float()
    dividend = String()
    dividend_rate = Float()
    estimated_dividend = Float()
    currency = String()
    acquisition_date = DateString()
    acquisition_price = Float()
    liquid = Boolean()
    capital_rate = Float()
    targetAssetId = String()
    sellBy = DateString()
    isTargetPool = Boolean()


# Payables


class PayablesQuery(ListQuery):
    flowClass = String()


class PayableIn(In):
    country = String(required=True)
    currency = String(required=True)
    description = String(required=True)
    amount = Float(
        required=True,
        metadata={"description": "Full size of the payment; informational only."},
    )
    balance = Float(required=True, metadata={"description": "Amount still due."})
    dueDate = DateString(required=True)
    commited = Boolean(allow_none=True)
    flowClass = String(required=True)
    targetAssetId = String(
        required=True, metadata={"description": "Account that pays it."}
    )


class PayableOut(Schema):
    id = Integer()
    country = String()
    currency = String()
    description = String()
    amount = Float()
    dueDate = DateString()
    commited = Boolean()
    balance = Float()
    flowClass = String()
    targetAssetId = String()


# Properties


class PropertyIn(In):
    country = String(required=True)
    currency = String(required=True)
    propertyName = String(required=True)
    purchasePrice = Float(required=True)
    purchaseDate = DateString(required=True)
    currentPrice = Float(required=True)
    rentPrice = Float(required=True)
    depreciation = Float(required=True)
    additionalData = String(required=True)
    rentCurrency = String(required=True)
    sellBy = DateString(allow_none=True)
    targetAssetId = String(allow_none=True)


class PropertyOut(Schema):
    id = Integer()
    country = String()
    currency = String()
    propertyName = String()
    purchasePrice = Float()
    purchaseDate = DateString()
    currentPrice = Float()
    rentPrice = Float()
    depreciation = Float()
    additionalData = String()
    rentCurrency = String()
    sellBy = DateString()
    targetAssetId = String()


# Projected and budgeted transactions


class MonthlyTransactionOut(Schema):
    id = String()
    assetId = String()
    amount = Float()
    currency = String()
    yearMonth = String()


class DashboardBudgetOut(Schema):
    id = String()
    label = String()
    amount = Float(metadata={"description": "Recorded so far this month."})
    budget = Float()
    currency = String()
    yearMonth = String()


# Bonds and deposit certificates


class CertificateIn(In):
    name = String(required=True)
    capital = Float(required=True)
    currency = String(required=True)
    maturityDate = DateString(required=True)
    rate = Float(required=True)
    entity = String(required=True)
    country = String(required=True)
    targetAssetId = String(required=True)


class CertificateOut(Schema):
    id = Integer()
    name = String()
    capital = Float()
    currency = String()
    maturityDate = DateString()
    rate = Float()
    entity = String()
    country = String()
    purchasePrice = String()
    targetAssetId = String()


# Same fields, separate classes so each has its own name in the OpenAPI spec.


class BondIn(CertificateIn):
    pass


class BondOut(CertificateOut):
    pass


class DepositCertificateIn(CertificateIn):
    pass


class DepositCertificateOut(CertificateOut):
    pass


class BondScheduleQuery(PageQuery):
    bondId = Integer()
    paid = Boolean()


class BondScheduleIn(In):
    bondId = Integer(required=True)
    transactionDate = DateString(required=True)
    amount = Float(required=True)
    paid = Boolean(allow_none=True)


class BondScheduleOut(Schema):
    id = Integer()
    bondId = Integer()
    transactionDate = DateString()
    amount = Float()
    paid = Boolean()


class DepositCertificateScheduleQuery(PageQuery):
    depositCertificateId = Integer()
    paid = Boolean()


class DepositCertificateScheduleIn(In):
    cdId = Integer(required=True)
    transactionDate = DateString(required=True)
    amount = Float(required=True)
    paid = Boolean(allow_none=True)


class DepositCertificateScheduleOut(Schema):
    id = Integer()
    depositCertificateId = Integer()
    transactionDate = DateString()
    amount = Float()
    paid = Boolean()


# Recurrents and their transactions


class RecurrentsQuery(PageQuery):
    flowClass = String()
    targetAssetId = String()


class RecurrentIn(In):
    id = String(required=True)
    assetId = String(allow_none=True, metadata={"description": "Parent asset."})
    targetAssetId = String(required=True)
    country = String(required=True)
    amount = Float(required=True)
    currency = String(required=True)
    recurrence = String(
        required=True,
        metadata={"description": "Cron pattern; runs at most once a month."},
    )
    start = DateString(required=True)
    end = DateString(required=True)
    flowClass = String(required=True)
    rate = Float(required=True)
    inflation = Boolean(allow_none=True)


class RecurrentOut(Schema):
    id = String()
    assetId = String()
    targetAssetId = String()
    country = String()
    amount = Float()
    currency = String()
    recurrence = String()
    start = DateString()
    end = DateString()
    flowClass = String()
    rate = Float()
    inflation = Boolean()


class RecurrentTransactionsQuery(PageQuery):
    recurrentId = String()
    yearMonth = String()
    paidWithAssetId = String()
    description = String(metadata={"description": "Substring match."})


class RecurrentTransactionIn(In):
    recurrentId = String(required=True)
    yearMonth = YearMonth(required=True)
    description = String(required=True, validate=Length(max=200))
    amount = Float(
        required=True,
        metadata={"description": "Negative for spending, positive for income."},
    )
    transactionDate = DateString(required=True)
    paidWithAssetId = String(required=True)
    updateBalance = Boolean(
        metadata={"description": "Also add the amount to the paying account."}
    )


class RecurrentTransactionOut(Schema):
    id = Integer()
    recurrentId = String()
    yearMonth = String()
    description = String()
    amount = Float()
    transactionDate = DateString()
    paidWithAssetId = String()
    createDate = String()
    importHash = String()
    currency = String(metadata={"description": "Only in lists: the recurrent's."})


# Statement import


class TransactionParserOut(Schema):
    id = String()
    name = String()
    description = String()
    extensions = List(String())
    maxBytes = Integer()


class ParseIn(In):
    parser = String(required=True, metadata={"description": "A transactionParsers id."})
    file = File(required=True)


class ParsedRowOut(Schema):
    importHash = String()
    transactionDate = DateString()
    yearMonth = String()
    description = String()
    amount = Float()
    recurrentId = String()
    paidWithAssetId = String()
    status = String(metadata={"description": "new, ignored or imported."})
    transactionId = Integer(metadata={"description": "Set when imported."})


class IgnoredRowIn(In):
    importHash = String(required=True)
    transactionDate = DateString(required=True)
    description = String()
    amount = Float(required=True)


class ImportRowIn(IgnoredRowIn):
    yearMonth = YearMonth(
        allow_none=True, metadata={"description": "Defaults to transactionDate's."}
    )
    recurrentId = String(required=True)
    paidWithAssetId = String(required=True)


class ImportIn(In):
    transactions = List(Nested(ImportRowIn))
    ignored = List(Nested(IgnoredRowIn))


class ImportOut(Schema):
    inserted = Integer()
    ignored = Integer()
    skipped = Integer()


# Reports


class ExchangeRateOut(Schema):
    id = String()
    rate = Float()
    weekChange = Float(metadata={"description": "Change over five business days."})


class FutureTimelineQuery(In):
    endDate = DateString(
        allow_none=True, metadata={"description": "Defaults to LAST_UNTIL."}
    )
    capitalGrowth = Boolean(
        metadata={"description": "Grow instruments by their capital rate."}
    )


class MonthlyPnlQuery(In):
    oneOff = Boolean(metadata={"description": "Include one-off flows."})


class JwtTokenQuery(In):
    expiration_hours = Integer(metadata={"description": "Token expiration in hours."})


class RecurrentHistoryQuery(In):
    startYearMonth = YearMonth(allow_none=True)
    endYearMonth = YearMonth(allow_none=True)
    flowClass = String(allow_none=True)


class UpcomingPaymentsQuery(PageQuery):
    exclude = Boolean(metadata={"description": "Leave out capital; defaults to true."})


class UpcomingPaymentOut(Schema):
    id = String()
    assetId = String()
    country = String()
    date = DateString()
    amount = Float()
    currency = String()
    capital = Boolean()


# Auth


class LoginIn(In):
    username = String(required=True)
    password = String(required=True)


class LoginOut(Schema):
    id = String()
    fullName = String()


class ProfileOut(Schema):
    id = String()
    username = String()
    name = String()
    email = String()
    config = Dict(metadata={"description": "The user's UserConfig, read-only."})
