class RecurrentTypes:
    Loan = "loan"
    Repayment = "repayment"
    Income = "income"
    Expense = "expense"
    Transfer = "transfer"


def is_transfer(asset) -> bool:
    """Transfers move value between assets in pairs; they're not income or expenses."""
    flow_class = getattr(asset, "flow_class", None) or ""
    return flow_class.lower() == RecurrentTypes.Transfer
