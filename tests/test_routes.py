# tests/test_routes.py
import pytest
from app import create_app
from app.database import initialize_database

@pytest.fixture
def client():
    initialize_database()  # Ensure DB is ready
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

# ----------------------
# AUTHENTICATION TESTS
# ----------------------
def test_login_page(client):
    rv = client.get("/login")
    assert rv.status_code == 200
    assert b"Login" in rv.data

def test_login_success(client):
    rv = client.post("/login", data={"username": "admin", "password": "admin"}, follow_redirects=True)
    assert b"Login successful" in rv.data
    assert b"Dashboard" in rv.data

def test_login_fail(client):
    rv = client.post("/login", data={"username": "admin", "password": "wrong"}, follow_redirects=True)
    assert b"Invalid credentials" in rv.data

# ----------------------
# DASHBOARD TESTS
# ----------------------
def test_dashboard_requires_login(client):
    rv = client.get("/", follow_redirects=True)
    assert b"Please log in" in rv.data

# ----------------------
# EMPLOYEE CRUD TESTS
# ----------------------
def test_add_employee(client):
    # login first
    with client.session_transaction() as sess:
        sess["manager_id"] = 1

    rv = client.post("/employees/add", data={
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "123456789",
        "max_hours": "40",
        "days_unavailable": "Sat,Sun"
    }, follow_redirects=True)
    assert b"Employee added successfully" in rv.data

def test_edit_employee(client):
    with client.session_transaction() as sess:
        sess["manager_id"] = 1
    # Add employee first (or use fixture)
    client.post("/employees/add", data={"name": "EditMe", "email": "edit@example.com"})
    rv = client.post("/employees/edit/1", data={
    "name": "Edited",
    "email": "edited@example.com",
    "phone": "123456789",
    "max_hours": "40",
    "days_unavailable": "Sat,Sun"
}, follow_redirects=True)

    assert b"Employee updated successfully" in rv.data

def test_delete_employee(client):
    with client.session_transaction() as sess:
        sess["manager_id"] = 1
    client.post("/employees/add", data={"name": "DeleteMe", "email": "delete@example.com"})
    rv = client.get("/employees/delete/1", follow_redirects=True)
    assert b"Employee deleted successfully" in rv.data
