import pytest
from app.database import get_db
import os
from app.routes import ROSTERS_DIR, generate_roster_pdf

# -----------------------------
# Helper for logging in
# -----------------------------
def login(client, username="admin", password="admin"):
    return client.post("/login", data={
        "username": username,
        "password": password
    }, follow_redirects=True)

# -----------------------------
# AUTHENTICATION TESTS
# -----------------------------
def test_login_logout(client):
    # GET login page
    rv = client.get("/login")
    assert b"Login" in rv.data

    # POST login
    rv = login(client)
    assert b"Login successful!" in rv.data

    # Logout
    rv = client.get("/logout", follow_redirects=True)
    assert b"You have been logged out." in rv.data

def test_change_password(client, app):
    login(client)

    # Incorrect old password
    rv = client.post("/change_password", data={
        "old_password": "wrong",
        "new_password": "newpass",
        "confirm_password": "newpass"
    }, follow_redirects=True)
    assert b"Old password is incorrect." in rv.data

    # Non-matching new passwords
    rv = client.post("/change_password", data={
        "old_password": "admin",
        "new_password": "newpass",
        "confirm_password": "diff"
    }, follow_redirects=True)
    assert b"New passwords do not match." in rv.data

    # Successful password change
    rv = client.post("/change_password", data={
        "old_password": "admin",
        "new_password": "newpass",
        "confirm_password": "newpass"
    }, follow_redirects=True)
    assert b"Password updated successfully!" in rv.data

# -----------------------------
# DASHBOARD TESTS
# -----------------------------
def test_dashboard_requires_login(client):
    rv = client.get("/", follow_redirects=True)
    assert b"Please log in to access this page." in rv.data

def test_dashboard_content(client, app):
    login(client)
    rv = client.get("/")
    assert rv.status_code == 200
    assert b"employee_count" not in rv.data  # template renders HTML, not var names

# -----------------------------
# EMPLOYEE CRUD TESTS
# -----------------------------
def test_add_edit_delete_employee(client, app):
    login(client)

    # Add employee
    rv = client.post("/employees/add", data={
        "name": "Alice",
        "email": "alice@test.com",
        "phone": "123456789",
        "max_hours": "40",
        "days_unavailable": ["Monday", "Tuesday"]
    }, follow_redirects=True)
    assert b"Employee added successfully" in rv.data

    # Verify DB entry
    with app.app_context():
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT * FROM staff WHERE name=?", ("Alice",))
        emp = cur.fetchone()
        assert emp is not None
        staff_id = emp["staff_id"]

    # Edit employee
    rv = client.post(f"/employees/edit/{staff_id}", data={
        "name": "Alice Smith",
        "email": "alice@test.com",
        "phone": "987654321",
        "max_hours": "35",
        "days_unavailable": ["Wednesday"]
    }, follow_redirects=True)
    assert b"Employee updated successfully" in rv.data

    # Delete employee
    rv = client.get(f"/employees/delete/{staff_id}", follow_redirects=True)
    assert b"Employee deleted successfully" in rv.data

# -----------------------------
# ROSTER TESTS
# -----------------------------


def test_roster_creation(client, app, tmp_path):
    login(client)

    # Override ROSTERS_DIR to temp folder
    test_rosters_dir = tmp_path / "Rosters"
    test_rosters_dir.mkdir()
    # monkeypatch the global variable in routes.py
    app.view_functions["main.rosters"].__globals__["ROSTERS_DIR"] = str(test_rosters_dir)
    app.view_functions["main.download_roster"].__globals__["ROSTERS_DIR"] = str(test_rosters_dir)

    start_date = "2025-10-05"
    end_date = "2025-10-10"
    pdf_filename = f"roster_{start_date}_{end_date}.pdf"
    pdf_path = test_rosters_dir / pdf_filename

    rv = client.post("/rosters", data={
        "start_date": start_date,
        "end_date": end_date,
        "company": "My Company",
        "department": "IT"
    }, follow_redirects=True)

    # Check flash message
    assert b"Roster created and PDF generated!" in rv.data
    # Check PDF file exists
    assert pdf_path.exists()

