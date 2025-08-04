from typing import Dict, Any

from g_tools import get_table

class Bond:
    def __init__(self, bond_id: str, capital: float, interest_rate: float, maturity_date: str, currency: str = "USD", name: str = ""):
        self.bond_id = bond_id
        self.capital = capital
        self.currency = currency
        self.interest_rate = interest_rate
        self.maturity_date = maturity_date

    def __repr__(self):
        return f"Bond ID: {self.bond_id}, Name: {self.bond_id}, Face Value: {self.capital}, Interest Rate: {self.interest_rate}, Maturity Date: {self.maturity_date}"
    

def parse_bond(data: Dict[str, Any]) -> Bond:
    """
    Function to parse account data from the provided data.

    :param data: List of lists containing the account data.
    :return: List of dictionaries with account information.
    """
    new_bond = Bond(
        bond_id=data["Name"],
        currency=data["Currency"],
        capital=float(data["Capital"].replace(",", "")),
        interest_rate=float(data["Interest"].replace("%", "")) / 100,
        maturity_date=data["Expiration"]
    )

    return new_bond


def fetch_bond(sheet: str) -> Bond:
    data = get_table(sheet, "Summary")
    if data[0][0] != "Type" or data[0][1] != "Bond":
        raise ValueError("The first cell of the Summary sheet must be 'Type' and the")
    bond_dict: Dict[str, Any] = {}
    for row in data:
        bond_dict[row[0]] = row[1]
   
    bond = parse_bond(bond_dict)
    
    return bond