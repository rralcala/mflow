from typing import List, Dict, Any

from g_tools import get_table, USDPYG


class Account:
    country: str
    institution: str
    account_id: str
    currency: str
    balance: float
    factor: float
    type: str

    def __init__(self, country: str, institution: str, account_id: str, currency: str, balance: float, factor: float = 1.0, type: str = "Savings"  ):
        self.country = country
        self.institution = institution
        self.account_id = account_id
        self.currency = currency
        self.balance = balance
        self.factor = factor
        self.type = type

    def deposit(self, amount: float):
        if amount > 0:
            self.balance += amount
            return True
        return False

    def withdraw(self, amount: float):
        if 0 < amount <= self.balance:
            self.balance -= amount
            return True
        return False

    def get_balance(self):
        return self.balance * self.factor

    def __str__(self):
        return f"Account ID: {self.account_id}, Balance: {self.balance}"


def parse_accounts(data: List[List[str]]) -> List[Account]:
    """
    Function to parse account data from the provided data.

    :param data: List of lists containing the account data.
    :return: List of dictionaries with account information.
    """
    parsed_accounts: List[Account] = []
    for row in data[1:]:  # Skip header row
        if len(row) < 8:
            continue  # Skip rows that do not have enough columns
        account = Account(
            country=row[0],
            institution=row[1], 
            account_id=row[2],
            currency=row[3],
            balance=float(row[4].replace(",", "")),
            factor=float(row[5].replace(",", "")),
            type=row[7]
        )
        parsed_accounts.append(account)

    return parsed_accounts


def fetch_accounts(sheet: str, worksheet: str):
    data = get_table(sheet, "Summary")

    if data[0][0] != "Type" or data[0][1] != "Cash":
        raise ValueError("The first cell of the Summary sheet must be 'Type' and the")

    ac_data = get_table(sheet, worksheet)
    accounts = parse_accounts(ac_data)
    total_balance = 0.0
    for account in accounts:
        if account.currency == "PYG":
            total_balance += account.balance / USDPYG
            #account["currency"] = "USD"
        else:
            total_balance += account.balance
    return accounts, total_balance