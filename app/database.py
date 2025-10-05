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
from werkzeug.security import generate_password_hash

# -------------------------
# Database Connection
# -------------------------
def get_db():
    """Return a SQLite3 connection for current Flask app context."""
    if 'db' not in g:
        db_path = current_app.config.get('DATABASE', 'roster.db')
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    """Close database connection if open."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


# -------------------------
# Constants
# -------------------------
DB_FILE = "roster.db"
ROSTERS_DIR = "Rosters"


def create_connection(db_file=None):
    """Create and return SQLite connection."""
    if db_file is None:
        db_file = current_app.config.get("DATABASE", DB_FILE)
    conn = sqlite3.connect(db_file)
    conn.execute("PRAGMA foreign_keys = ON")  # Ensure FK constraints
    return conn


# -------------------------
# Table Creation
# -------------------------
def create_tables(conn):
    """Create all necessary tables if they don't already exist."""
    cursor = conn.cursor()

    # Managers
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS managers (
            manager_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT NOT NULL UNIQUE,
            password   TEXT NOT NULL
        )
    """)

    # Company info
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS company_info (
            company_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name    TEXT NOT NULL,
            department_name TEXT
        )
    """)

    # Employees / Staff
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

    # Roster summary
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS roster (
            roster_id  INTEGER PRIMARY KEY AUTOINCREMENT,
            start_date TEXT,
            end_date   TEXT,
            pdf_file   TEXT,  -- Path to the generated PDF
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            edited_on  TEXT
        )
    """)

    # Roster assignments (dynamic multiple employees per day/shift)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS roster_assignments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            roster_id   INTEGER NOT NULL,
            employee_id INTEGER NOT NULL,
            duty_date   TEXT NOT NULL,
            shift       TEXT,
            hours       TEXT,
            note        TEXT,
            start_time   TEXT,
            end_time     TEXT,       
            FOREIGN KEY(roster_id) REFERENCES roster(roster_id) ON DELETE CASCADE,
            FOREIGN KEY(employee_id) REFERENCES staff(staff_id) ON DELETE CASCADE
        )
    """)

    conn.commit()


# -------------------------
# Seed Defaults
# -------------------------
def seed_default_manager(conn):
    """Insert default admin if no managers exist."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM managers")
    count = cursor.fetchone()[0]
    if count == 0:
        hashed_password = generate_password_hash("admin")
        cursor.execute(
            "INSERT INTO managers (username, password) VALUES (?, ?)",
            ("admin", hashed_password)
        )
        print("[✔] Default manager created — username='admin', password='admin'")
        conn.commit()


def seed_company_info(conn):
    """Insert placeholder company info if not present."""
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


# -------------------------
# PDF Folder
# -------------------------
def ensure_rosters_folder():
    """Ensure that the directory for storing generated roster PDFs exists."""
    os.makedirs(ROSTERS_DIR, exist_ok=True)


# -------------------------
# Full Initialization
# -------------------------
def initialize_database():
    """Run full initialization: tables, default admin, company info, PDF folder."""
    conn = create_connection()
    create_tables(conn)
    seed_default_manager(conn)
    seed_company_info(conn)
    conn.close()
    ensure_rosters_folder()


# -------------------------
# Run standalone
# -------------------------
if __name__ == "__main__":
    initialize_database()
    print("[✔] Database initialized and ready.")
    print(f"[✔] PDF storage folder ensured at '{ROSTERS_DIR}/'")