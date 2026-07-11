import sqlite3

_DATABASE_PATH = "data/database.db"

def get_sqlite_db():
    conn = sqlite3.connect(_DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_sqlite():
    conn = get_sqlite_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS members (
            ingame_id TEXT PRIMARY KEY,
            ingame_name TEXT NOT NULL,
            discord_id TEXT,
            discord_username TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS fan_requirements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month_year TEXT NOT NULL,
            day_start INTEGER NOT NULL,
            day_end INTEGER NOT NULL,
            daily_fan INTEGER NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS member_exemptions (
            ingame_id TEXT PRIMARY KEY,
            reason TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS member_extras (
            ingame_id TEXT,
            month_year TEXT,
            extra INTEGER,
            PRIMARY KEY(ingame_id, month_year)
        )
    ''')
    conn.commit()
    conn.close()

# Auto-initialize sqlite on load
init_sqlite()
