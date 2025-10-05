import pytest
from app.database import get_db

# Utility to login
def login(client):
    return client.post("/login", data={"username": "admin", "password": "admin"}, follow_redirects=True)

def test_add_edit_delete_employee(client, app):
    login(client)

    # Add employee
    rv = client.post("/employees/add", data={
        "name": "Alice",
        "email": "alice@test.com",
        "phone": "123456789",
        "max_hours": "40",
        "days_unavailable": ""
    }, follow_redirects=True)
    assert b"Employee added successfully" in rv.data

    # Edit employee
    with app.app_context():
        db = get_db()
        staff_id = db.execute("SELECT staff_id FROM staff WHERE name='Alice'").fetchone()["staff_id"]

    rv = client.post(f"/employees/edit/{staff_id}", data={
        "name": "Alice Edited",
        "email": "alice@test.com",
        "phone": "987654321",
        "max_hours": "35",
        "days_unavailable": ""
    }, follow_redirects=True)
    assert b"Employee updated successfully" in rv.data

    # Delete employee
    rv = client.get(f"/employees/delete/{staff_id}", follow_redirects=True)
    assert b"Employee deleted successfully" in rv.data
