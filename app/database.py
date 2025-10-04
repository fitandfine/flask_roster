"""
database.py — Handles SQLite database setup and initialization
for the Flask Roster Management System.

This module:
    • Creates database connection
    • Builds all required tables
    • Seeds a default admin user if none exists
    • Ensures PDF storage folder exists
    • Stores company and department info for PDF headers
"""

import sqlite3
import os
from flask import current_app, g

def get_db():
    """Return a SQLite3 connection for current Flask app context."""
    if 'db' not in g:
        db_path = current_app.config.get('DATABASE', 'roster.db')
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    """Close database connection if open."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

# Constants
DB_FILE = "roster.db"
ROSTERS_DIR = "Rosters"


def create_connection(db_file=DB_FILE):
    """
    Create and return a SQLite connection.

    Args:
        db_file (str): Path to the database file.
    Returns:
        sqlite3.Connection: A SQLite connection object.
    """
    return sqlite3.connect(db_file)


def create_tables(conn):
    """
    Create all necessary tables if they don't already exist.
    """

    cursor = conn.cursor()

    # Table for manager credentials
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS managers (
            manager_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT NOT NULL UNIQUE,
            password   TEXT NOT NULL
        )
    """)

    # Table for company information
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS company_info (
            company_id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            department_name TEXT
        )
    """)

    # Table for employee/staff details
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS staff (
            staff_id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name             TEXT NOT NULL,
            email            TEXT NOT NULL,
            phone_number     TEXT,
            max_hours        TEXT,
            days_unavailable TEXT
        )
    """)

    # Table for roster summary
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS roster (
            roster_id  INTEGER PRIMARY KEY AUTOINCREMENT,
            start_date TEXT,
            end_date   TEXT,
            pdf_file   TEXT,  -- Path to the generated PDF file
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Table for duty details (with optional notes)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS roster_duties (
            roster_id  INTEGER,
            duty_date  TEXT,
            employee   TEXT,
            start_time TEXT,
            end_time   TEXT,
            note       TEXT,
            FOREIGN KEY(roster_id) REFERENCES roster(roster_id) ON DELETE CASCADE
        )
    """)

    conn.commit()


def seed_default_manager(conn):
    """
    Insert a default admin manager if none exist.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM managers")
    count = cursor.fetchone()[0]
    if count == 0:
        cursor.execute(
            "INSERT INTO managers (username, password) VALUES (?, ?)",
            ("admin", "admin")
        )
        print("[✔] Default manager created — username='admin', password='admin'")
        conn.commit()


def seed_company_info(conn):
    """
    Insert a placeholder company info row if not present.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM company_info")
    count = cursor.fetchone()[0]
    if count == 0:
        cursor.execute(
            "INSERT INTO company_info (company_name, department_name) VALUES (?, ?)",
            ("My Company", "General Department")
        )
        print("[✔] Default company info added.")
        conn.commit()


def ensure_rosters_folder():
    """
    Ensure that the directory for storing generated roster PDFs exists.
    """
    os.makedirs(ROSTERS_DIR, exist_ok=True)


def initialize_database():
    """
    Run full initialization: tables, default admin, company info, PDF folder.
    """
    conn = create_connection()
    create_tables(conn)
    seed_default_manager(conn)
    seed_company_info(conn)
    conn.close()
    ensure_rosters_folder()


if __name__ == "__main__":
    initialize_database()
    print("[✔] Database initialized and ready.")
