import pytest
import json
from app.database import get_db

# Utility to login
def login(client):
    return client.post("/login", data={"username": "admin", "password": "admin"}, follow_redirects=True)

def test_roster_creation_and_pdf(client, tmp_path, app):
    login(client)

    # Add staff member
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO staff (name,email,phone_number,max_hours,days_unavailable) VALUES (?,?,?,?,?)",
            ("Test Staff", "test@example.com", "123456789", "40", "")
        )
        db.commit()
        staff_id = db.execute("SELECT staff_id FROM staff WHERE name='Test Staff'").fetchone()["staff_id"]

    # Assignments JSON
    assignments = [
        {"employee_id": staff_id, "duty_date": "2025-10-06", "start_time": "09:00", "end_time": "17:00", "note": ""}
    ]

    # Override roster folder for test
    roster_dir = tmp_path / "Rosters"
    roster_dir.mkdir(exist_ok=True)
    client.application.view_functions["main.rosters"].__globals__["ROSTERS_DIR"] = str(roster_dir)
    client.application.view_functions["main.download_roster"].__globals__["ROSTERS_DIR"] = str(roster_dir)

    rv = client.post("/rosters", data={
        "start_date": "2025-10-06",
        "end_date": "2025-10-06",
        "company": "My Company",
        "department": "IT",
        "assignments": json.dumps(assignments)
    }, follow_redirects=True)

    assert rv.status_code == 200
    assert b"Roster saved successfully!" in rv.data
