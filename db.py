import sqlite3

class DB:
    def __init__(self) -> None:
        self.con = sqlite3.connect('my-library.db')
        self.cur = self.con.cursor()
        self._init_db()
    
    def _init_db(self):
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY,
                title TEXT,
                author TEXT,
                year INTEGER
            )
            """)