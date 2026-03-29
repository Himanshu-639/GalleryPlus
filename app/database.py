"""Database initialization and helper queries."""

import sqlite3
from app.config import DB_PATH


def init_db():
    """Create database tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS people (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    encoding BLOB
                 )''')
    c.execute('''CREATE TABLE IF NOT EXISTS photos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filepath TEXT UNIQUE
                 )''')
    c.execute('''CREATE TABLE IF NOT EXISTS photo_faces (
                    person_id INTEGER,
                    photo_id INTEGER,
                    FOREIGN KEY(person_id) REFERENCES people(id),
                    FOREIGN KEY(photo_id) REFERENCES photos(id),
                    UNIQUE(person_id, photo_id)
                 )''')
    conn.commit()
    conn.close()


def get_connection():
    """Return a new SQLite connection to the app database."""
    return sqlite3.connect(DB_PATH)
