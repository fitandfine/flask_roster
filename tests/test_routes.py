"""
test_routes.py
---------------
Pytest test suite for all major routes in the Flask Roster app.
"""

import pytest
import os
from app.routes import bp, DB_FILE
from app import create_app

@pytest.fixture
def client(tmp_path):
    """Create a test client with temporary database."""
    test_db = tmp_path / "test.db"
    os.makedirs(tmp_path, exist_ok=True)

    app = create_app({
        "TESTING": True,
        "DATABASE": str(test_db)
    })
  

    with app.test_client() as client:
        yield client


def test_login_page(client):
    """Login page loads successfully."""
    rv = client.get("/login")
    assert rv.status_code == 200
    assert b"Login" in rv.data


def test_dashboard_requires_login(client):
    """Dashboard requires login."""
    rv = client.get("/")
    assert rv.status_code == 302  # Redirects to login


def test_add_employee_after_login(client):
    """Ensure adding employee works after login."""
    with client.session_transaction() as sess:
        sess["manager_id"] = 1
    rv = client.post("/employees/add", data={
        "name": "John Doe",
        "email": "john@example.com"
    }, follow_redirects=True)
    assert b"Employee added successfully" in rv.data
