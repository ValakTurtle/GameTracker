import sqlite3

DB_NAME = "games.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # So we can access columns by name
    return conn

def create_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            platform TEXT,
            status TEXT,
            rating INTEGER,
            cover_url TEXT,
            notes TEXT,
            start_date TEXT,
            finish_date TEXT
        )
    """)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_table()
    print("Database and 'games' table created (if not exists).")
