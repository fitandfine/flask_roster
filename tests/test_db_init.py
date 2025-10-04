"""
test_db_init.py — Tests for database initialization logic.
"""

import sqlite3
from app.database import initialize_database, create_connection, DB_FILE

def test_database_initialization(tmp_path):
    """Ensure database and tables are created properly."""
    db_path = tmp_path / "test_roster.db"
    conn = create_connection(db_file=db_path)
    from app.database import create_tables, seed_default_manager, seed_company_info

    create_tables(conn)
    seed_default_manager(conn)
    seed_company_info(conn)

    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    assert "managers" in tables
    assert "staff" in tables
    assert "roster" in tables
    assert "roster_duties" in tables
    assert "company_info" in tables
