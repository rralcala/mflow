import sqlite3


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
