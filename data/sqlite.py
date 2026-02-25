import sqlite3

from lib.config import Config


def insert_recurrent(
    identifier: str,
    parent_asset_id: str,
    country: str,
    amount: float,
    currency: str,
    recurrence: str,
    start: str,
    end: str,
    flow_class: str,
    rate: float = 0.0,
):
    # Connect to the database (creates 'mydatabase.db' if it doesn't exist)
    conn = sqlite3.connect(Config.BASE_PATH + "mydatabase.db")
    cursor = conn.cursor()

    # Insert a new transaction
    cursor.execute(
        "REPLACE INTO recurrent (identifier, parent_asset_id, country, amount, currency, recurrence, start, end, flow_class, rate) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            identifier,
            parent_asset_id,
            country,
            str(amount),
            currency,
            recurrence,
            start,
            end,
            flow_class,
            str(rate),
        ),
    )

    # Commit the changes to the database
    conn.commit()
    conn.close()


def get_transactions_for_asset_id(
    base_path: str, asset_id: str
) -> list[tuple[str, str, str, float, float, str, str, str, str]]:
    conn = sqlite3.connect(base_path + "mydatabase.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, description, amount, balance, date, time, origin, tags FROM account_transactions WHERE asset_id = ? ORDER BY date ASC, time ASC",
        (asset_id,),
    )
    rows = cursor.fetchall()

    # Close the connection
    conn.close()
    return rows


def find_accounts(base_path: str) -> list[str]:
    conn = sqlite3.connect(base_path + "mydatabase.db")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT asset_id FROM account_transactions")
    rows = cursor.fetchall()

    # Close the connection
    conn.close()
    return rows


def save_summary(base_path: str, date: str, value: str):
    # Connect to the database (creates 'mydatabase.db' if it doesn't exist)
    conn = sqlite3.connect(base_path + "mydatabase.db")
    cursor = conn.cursor()

    # Create a table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            date TEXT NOT NULL PRIMARY KEY ,
            value TEXT NOT NULL
        )
    """)

    cursor.execute("REPLACE INTO history (date, value) VALUES (?, ?)", (date, value))

    # Commit the changes to the database
    conn.commit()
    conn.close()


def read_history(base_path: str, num_records: int) -> list[tuple[str, str]]:
    conn = sqlite3.connect(base_path + "mydatabase.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM history ORDER BY date DESC LIMIT ?", (num_records,))
    rows = cursor.fetchall()

    # Close the connection
    conn.close()
    return rows
