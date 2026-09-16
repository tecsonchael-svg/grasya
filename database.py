"""
database.py — persistent storage for the resort scheduler.

Uses SQLite via Python's built-in sqlite3 module (no extra packages to
install). Bookings are stored in a single 'bookings' table so they
survive a server restart, instead of living only in a Python list in
memory.
"""

import sqlite3
from pathlib import Path

# The .db file lives next to this script, so it works the same
# whether you run the app from this folder or import it elsewhere.
DB_PATH = Path(__file__).parent / "resort.db"


def get_connection():
    """Open a new connection. sqlite3 connections are cheap and are
    not shared across requests, which keeps things simple and safe
    for Flask's default threaded dev server."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create the bookings table if it doesn't exist yet. Safe to call
    every time the app starts."""
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS bookings (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT NOT NULL,
            check_in  TEXT NOT NULL,   -- stored as 'YYYY-MM-DD'
            check_out TEXT NOT NULL,   -- stored as 'YYYY-MM-DD'
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()
    conn.close()


def fetch_all_bookings():
    """Return every booking row as a list of sqlite3.Row objects
    (dict-like: row['name'], row['check_in'], etc.)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, name, check_in, check_out FROM bookings"
    ).fetchall()
    conn.close()
    return rows


def insert_booking(name, check_in_str, check_out_str):
    """Insert a new booking. Dates are passed in as 'YYYY-MM-DD' strings.
    Returns the new row's id."""
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO bookings (name, check_in, check_out) VALUES (?, ?, ?)",
        (name, check_in_str, check_out_str),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def delete_booking(booking_id):
    """Delete a booking by its id. No-op if the id doesn't exist."""
    conn = get_connection()
    conn.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
    conn.commit()
    conn.close()