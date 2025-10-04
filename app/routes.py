"""
routes.py
----------
Main route definitions for the Flask Roster Management System.

This file handles:
- Authentication (login/logout/change password)
- Dashboard summary
- Employee CRUD operations
- Roster creation & PDF generation

All routes are designed to be intuitive, secure, and production-grade.
"""

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    session, flash, send_from_directory
)
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# --- CONFIGURATION ---
bp = Blueprint("main", __name__)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_FILE = os.path.join(BASE_DIR, "..", "roster.db")
ROSTERS_DIR = "Rosters"


@bp.before_request
def require_login():
    # Allow login page and static files without session
    if "manager_id" not in session and request.endpoint not in ("main.login", "main.static"):
        flash("Please log in to access this page.", "warning")
        return redirect(url_for("main.login"))

# ---------------------- #
#  DATABASE UTILITIES    #
# ---------------------- #
def get_db():
    """Return a SQLite3 connection."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------- #
#  AUTHENTICATION ROUTES #
# ---------------------- #
@bp.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate manager using username and password."""
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM managers WHERE username = ?", (username,))
        manager = cur.fetchone()

        if manager and check_password_hash(manager["password"], password):
            session["manager_id"] = manager["manager_id"]
            session["username"] = manager["username"]
            flash("Login successful!", "success")
            return redirect(url_for("main.dashboard"))
        else:
            flash("Invalid credentials. Try again.", "danger")

    return render_template("login.html")


@bp.route("/logout")
def logout():
    """End manager session."""
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.login"))


@bp.route("/change_password", methods=["GET", "POST"])
def change_password():
    """Allow logged-in manager to change password."""
    if "manager_id" not in session:
        return redirect(url_for("main.login"))

    if request.method == "POST":
        old_pass = request.form["old_password"]
        new_pass = request.form["new_password"]
        confirm_pass = request.form["confirm_password"]

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT password FROM managers WHERE manager_id = ?", (session["manager_id"],))
        current_hash = cur.fetchone()["password"]

        if not check_password_hash(current_hash, old_pass):
            flash("Old password is incorrect.", "danger")
        elif new_pass != confirm_pass:
            flash("New passwords do not match.", "danger")
        else:
            new_hash = generate_password_hash(new_pass)
            cur.execute("UPDATE managers SET password = ? WHERE manager_id = ?", (new_hash, session["manager_id"]))
            conn.commit()
            flash("Password updated successfully!", "success")
            return redirect(url_for("main.dashboard"))

    return render_template("change_password.html")


# ---------------------- #
#  DASHBOARD             #
# ---------------------- #

from flask import render_template, session, redirect, url_for
from datetime import date
from .database import get_db

@bp.route("/")
def dashboard():
    """
    Display the manager dashboard with live summary information.
    --------------------------------------------------------------
    Shows:
        • Total number of registered employees
        • The most recent roster created (start and end date)
        • List of employees on duty today
    """

    # Redirect to login if manager not authenticated
    if "manager_id" not in session:
        return redirect(url_for("main.login"))

    conn = get_db()
    cursor = conn.cursor()

    # --- 1. Employee Count ---
    cursor.execute("SELECT COUNT(*) FROM staff")
    employee_count = cursor.fetchone()[0]

    # --- 2. Most Recent Roster ---
    cursor.execute("SELECT * FROM roster ORDER BY created_at DESC LIMIT 1")
    latest_roster = cursor.fetchone()

    # --- 3. Today's Duties ---
    today = date.today().strftime("%Y-%m-%d")
    cursor.execute("SELECT * FROM roster_duties WHERE duty_date=?", (today,))
    today_duties = cursor.fetchall()

    # --- 4. Optional: If no recent roster exists, handle gracefully ---
    if latest_roster is None:
        latest_roster = {
            "start_date": "N/A",
            "end_date": "N/A"
        }

    # --- 5. Pass all data to template ---
    return render_template(
        "dashboard.html",
        username=session.get("username"),
        employee_count=employee_count,
        latest_roster=latest_roster,
        today_duties=today_duties
    )


# ---------------------- #
#  EMPLOYEE MANAGEMENT   #
# ---------------------- #
@bp.route("/employees", strict_slashes=False)
def employees():
    """List all employees."""
    if "manager_id" not in session:
        return redirect(url_for("main.login"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM staff ORDER BY name ASC")
    employees = cur.fetchall()
    return render_template("employees.html", employees=employees)


@bp.route("/employees/add", methods=["GET", "POST"])
def add_employee():
    if "manager_id" not in session:
        return redirect(url_for("main.login"))
    """Add a new employee with unavailable days."""
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        max_hours = request.form["max_hours"]

        # Unavailable days as list of checkbox inputs
        days = request.form.getlist("days_unavailable")
        days_unavailable = ",".join(days)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO staff (name, email, phone_number, max_hours, days_unavailable) VALUES (?, ?, ?, ?, ?)",
            (name, email, phone, max_hours, days_unavailable),
        )
        conn.commit()
        flash("Employee added successfully", "success")
        return redirect(url_for("main.employees"))

    return render_template("employee_form.html", action="Add")



@bp.route("/employees/edit/<int:staff_id>", methods=["GET", "POST"])
def edit_employee(staff_id):
    if "manager_id" not in session:
        return redirect(url_for("main.login"))
    """Edit an existing employee."""
    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        max_hours = request.form["max_hours"]
        days = request.form.getlist("days_unavailable")
        days_unavailable = ",".join(days)

        cursor.execute("""
            UPDATE staff SET name=?, email=?, phone_number=?, max_hours=?, days_unavailable=? WHERE staff_id=?
        """, (name, email, phone, max_hours, days_unavailable, staff_id))
        conn.commit()
        flash("Employee updated successfully", "info")
        return redirect(url_for("main.employees"))

    cursor.execute("SELECT * FROM staff WHERE staff_id=?", (staff_id,))
    employee = cursor.fetchone()
    return render_template("employee_form.html", employee=employee, action="Edit")



@bp.route("/employees/delete/<int:staff_id>", methods=["GET","POST"])
def delete_employee(staff_id):
    if "manager_id" not in session:
        return redirect(url_for("main.login"))
    """Delete an employee by ID."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM staff WHERE staff_id=?", (staff_id,))
    conn.commit()
    flash("Employee deleted successfully", "danger")
    return redirect(url_for("main.employees"))



# ---------------------- #
#  ROSTER MANAGEMENT     #
# ---------------------- #
@bp.route("/rosters", methods=["GET", "POST"])
def rosters():
    """List and create new rosters."""
    if "manager_id" not in session:
        return redirect(url_for("main.login"))

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        start_date = request.form["start_date"]
        end_date = request.form["end_date"]
        company = request.form["company"]
        department = request.form["department"]

        pdf_filename = f"roster_{start_date}_{end_date}.pdf"
        pdf_path = os.path.join(ROSTERS_DIR, pdf_filename)

        # Insert roster record
        cur.execute(
            "INSERT INTO roster (start_date, end_date, pdf_file) VALUES (?, ?, ?)",
            (start_date, end_date, pdf_filename)
        )
        conn.commit()
        roster_id = cur.lastrowid

        # Generate PDF
        generate_roster_pdf(pdf_path, company, department, start_date, end_date)

        flash("Roster created and PDF generated!", "success")
        return redirect(url_for("main.rosters"))

    cur.execute("SELECT * FROM roster ORDER BY created_at DESC")
    rosters_list = cur.fetchall()
    return render_template("rosters.html", rosters=rosters_list)


def generate_roster_pdf(filepath, company, department, start, end):
    """Generate roster summary PDF."""
    c = canvas.Canvas(filepath, pagesize=A4)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(300, 800, company)
    c.setFont("Helvetica", 14)
    c.drawCentredString(300, 780, f"Department: {department}")
    c.setFont("Helvetica", 12)
    c.drawString(100, 750, f"Roster Period: {start} to {end}")
    c.line(50, 740, 550, 740)
    c.save()


@bp.route("/rosters/download/<filename>")
def download_roster(filename):
    """Download generated roster PDF."""
    return send_from_directory(ROSTERS_DIR, filename, as_attachment=True)
