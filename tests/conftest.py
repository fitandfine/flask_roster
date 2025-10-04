import pytest
import os
from app import create_app
from app.database import get_db, close_db, create_tables, seed_default_manager, seed_company_info, ensure_rosters_folder

@pytest.fixture
def app(tmp_path):
    """Create and configure a new app instance for each test."""
    db_path = tmp_path / "test_roster.db"

    app = create_app({
        "TESTING": True,
        "DATABASE": str(db_path)
    })

    # Initialize tables and seed data in test DB
    with app.app_context():
        conn = get_db()
        create_tables(conn)
        seed_default_manager(conn)
        seed_company_info(conn)
        conn.close()
        ensure_rosters_folder()

    yield app

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()
