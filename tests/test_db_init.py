import os
import sqlite3
from app.database import create_connection, create_tables, seed_default_manager, seed_company_info, ensure_rosters_folder

def test_tables_created(tmp_path):
    db_path = tmp_path / "db_test.db"
    conn = create_connection(db_path)
    create_tables(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()

    assert set(tables) >= {"managers", "staff", "roster", "roster_duties", "company_info"}

def test_default_manager_and_company(tmp_path):
    db_path = tmp_path / "db_seed.db"
    conn = create_connection(db_path)
    create_tables(conn)
    seed_default_manager(conn)
    seed_company_info(conn)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM managers WHERE username='admin'")
    manager = cursor.fetchone()
    assert manager is not None

    cursor.execute("SELECT * FROM company_info")
    company = cursor.fetchone()
    assert company is not None
    conn.close()

def test_rosters_folder_created(tmp_path):
    folder_path = tmp_path / "Rosters"
    os.makedirs(folder_path, exist_ok=True)
    assert folder_path.exists()
