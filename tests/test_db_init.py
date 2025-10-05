import pytest
from pathlib import Path
from app.database import create_connection, create_tables, seed_default_manager, seed_company_info

def test_tables_created(tmp_path: Path):
    db_path = tmp_path / "test.db"
    conn = create_connection(db_path)
    create_tables(conn)

    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    conn.close()

    expected_tables = {"managers", "staff", "roster", "roster_assignments", "company_info"}
    assert tables >= expected_tables

def test_seed_default_manager(tmp_path: Path):
    db_path = tmp_path / "test.db"
    conn = create_connection(db_path)
    create_tables(conn)
    seed_default_manager(conn)

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM managers WHERE username='admin'")
    admin = cursor.fetchone()
    conn.close()

    assert admin is not None
    assert admin[1] == "admin"  # username

def test_seed_company_info(tmp_path: Path):
    db_path = tmp_path / "test.db"
    conn = create_connection(db_path)
    create_tables(conn)
    seed_company_info(conn)

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM company_info")
    info = cursor.fetchone()
    conn.close()

    assert info is not None
    assert info[1] == "My Company"
