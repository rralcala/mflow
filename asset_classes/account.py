import logging
from typing import List

from g_tools import get_table, get_sheet_settings, USDPYG


class Account:

    def __init__(
        self,
        country: str,
        institution: str,
        account_id: str,
        currency: str,
        balance: float,
        factor: float = 1.0,
        account_type: str = "Savings",
    ):
        self.country = country
        self.institution = institution
        self.account_id = account_id
        self.currency = currency
        self.balance = balance
        self.factor = factor
        self.account_type = account_type

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
            account_type=row[7],
        )
        parsed_accounts.append(account)

    return parsed_accounts

def get_total_value(accounts: List[Account]) -> float:
    """
    Returns the total value of all accounts in USD.
    """
    total_value = 0.0
    for account in accounts:
        
        if account.currency == "PYG":
            value = account.get_balance() / USDPYG
        else:
            value = account.get_balance()
        total_value += value
        #logging.debug(f"{account.institution} {account.account_id}: {value}")
    return total_value

def fetch_accounts(sheet: str, worksheet: str):
    data = get_sheet_settings(sheet)

    if "itype" not in data or data["itype"].lower() != "cash":
        raise ValueError("The first cell of the Summary sheet must be 'Type' and the")

    ac_data = get_table(sheet, worksheet)
    accounts = parse_accounts(ac_data)
    return accounts

def print_accounts(accounts: List[Account]):
    """
    Function to print account information in a formatted way.

    :param accounts: List of dictionaries containing account information.
    """
    print(f"{'Name':<30} {'Balance':<15} {'Currency':<10}")
    total_balance = 0.0
    for account in accounts:
        if account.currency == "PYG":
            balance = account.balance / USDPYG
        else:
            balance = account.balance
        total_balance += balance

        print(f"{account.account_id:<30} {balance:<15.2f} {account.currency:<10}")
    print(f"{'Total':<30} {total_balance:<15.2f} USD")