from typing import List, Dict, Any

from asset_classes.portfolio import fetch_portfolio
from asset_classes.account import fetch_accounts, Account
from asset_classes.bond import fetch_bond
USDPYG = 7500


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


def print_table(data: List[List[str]]):
    """
    Function to print the data in a formatted way.

    :param data: List of lists containing the data to be printed.
    """
    for row in data:
        print("\t".join(row))


# Authenticate with your service account credentials
# Replace 'path/to/your/service_account.json' with the actual path

accounts, total_balance = fetch_accounts("CASH", "Accounts")
print_accounts(accounts)

portfolio, balance = fetch_portfolio("PORTFOLIO-1", "Portfolio")
#print_accounts(portfolio)
total_balance += balance
bond = fetch_bond("BOND-Tapepora-1")
print(f"\nBond Information:\n{bond}")
total_balance += bond.capital / USDPYG if bond.currency == "PYG" else bond.capital

bond = fetch_bond("BOND-Telecel-1")
print(f"\nBond Information:\n{bond}")
total_balance += bond.capital / USDPYG if bond.currency == "PYG" else bond.capital

print(f"{'Grand Total':<30} {total_balance:<15.2f}")
