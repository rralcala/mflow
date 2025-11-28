import sqlite3

from lib.config import BASE_PATH

def save_summary(date: str, value: str):
    # Connect to the database (creates 'mydatabase.db' if it doesn't exist)
    conn = sqlite3.connect(BASE_PATH + 'mydatabase.db')
    cursor = conn.cursor()

    # Create a table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            date TEXT NOT NULL PRIMARY KEY ,
            value TEXT NOT NULL
        )
    ''')

    cursor.execute("REPLACE INTO history (date, value) VALUES (?, ?)", (date, value))

    # Commit the changes to the database
    conn.commit()
    conn.close()

def read_history():
    # Optional: Verify the insertion by selecting data
    conn = sqlite3.connect(BASE_PATH + 'mydatabase.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM history")
    rows = cursor.fetchall()
    print("Data in 'history' table:")
    for row in rows:
        print(row)

    # Close the connection
    conn.close()