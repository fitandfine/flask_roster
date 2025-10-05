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
    session, flash, send_from_directory, current_app
)
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
from flask import jsonify, send_file
import math
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
import json
import smtplib
from email.message import EmailMessage

from .database import get_db

# --- CONFIGURATION ---
bp = Blueprint("main", __name__)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ROSTERS_DIR = os.path.join(BASE_DIR, "Rosters")
os.makedirs(ROSTERS_DIR, exist_ok=True)


# -------------------------
# Require login decorator
# -------------------------
@bp.before_request
def require_login():
    if "manager_id" not in session and request.endpoint not in ("main.login", "main.static"):
        flash("Please log in to access this page.", "warning")
        return redirect(url_for("main.login"))


# -------------------------
# Authentication Routes
# -------------------------
@bp.route("/login", methods=["GET", "POST"])
def login():
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
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.login"))


@bp.route("/change_password", methods=["GET", "POST"])
def change_password():
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


# -------------------------
# Dashboard
# -------------------------
@bp.route("/")
def dashboard():
    conn = get_db()
    cursor = conn.cursor()

    # Employee count
    cursor.execute("SELECT COUNT(*) FROM staff")
    employee_count = cursor.fetchone()[0]

    # Most recent roster
    cursor.execute("SELECT * FROM roster ORDER BY created_at DESC LIMIT 1")
    latest_roster = cursor.fetchone()
    if latest_roster is None:
        latest_roster = {"start_date": "N/A", "end_date": "N/A"}

    # Today's duties
    today_str = date.today().strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT s.name, ra.shift, ra.hours, ra.note
        FROM roster_assignments ra
        JOIN staff s ON ra.employee_id = s.staff_id
        WHERE ra.duty_date = ?
        ORDER BY ra.shift
    """, (today_str,))
    today_duties = cursor.fetchall()

    return render_template(
        "dashboard.html",
        username=session.get("username"),
        employee_count=employee_count,
        latest_roster=latest_roster,
        today_duties=today_duties
    )


# -------------------------
# Employee Management
# -------------------------
@bp.route("/employees", strict_slashes=False)
def employees():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM staff ORDER BY name ASC")
    employees = cur.fetchall()
    return render_template("employees.html", employees=employees)


@bp.route("/employees/add", methods=["GET", "POST"])
def add_employee():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        max_hours = request.form["max_hours"]
        days_unavailable = ",".join(request.form.getlist("days_unavailable"))

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
    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        max_hours = request.form["max_hours"]
        days_unavailable = ",".join(request.form.getlist("days_unavailable"))

        cursor.execute("""
            UPDATE staff SET name=?, email=?, phone_number=?, max_hours=?, days_unavailable=? WHERE staff_id=?
        """, (name, email, phone, max_hours, days_unavailable, staff_id))
        conn.commit()
        flash("Employee updated successfully", "info")
        return redirect(url_for("main.employees"))

    cursor.execute("SELECT * FROM staff WHERE staff_id=?", (staff_id,))
    employee = cursor.fetchone()
    return render_template("employee_form.html", employee=employee, action="Edit")


@bp.route("/employees/delete/<int:staff_id>", methods=["GET", "POST"])
def delete_employee(staff_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM staff WHERE staff_id=?", (staff_id,))
    conn.commit()
    flash("Employee deleted successfully", "danger")
    return redirect(url_for("main.employees"))


# -------------------------
# Roster Management
# -------------------------
@bp.route("/rosters", methods=["GET", "POST"])
def rosters():
    conn = get_db()
    cur = conn.cursor()

    # Employees
    cur.execute("SELECT * FROM staff ORDER BY name ASC")
    employees = [dict(emp) for emp in cur.fetchall()]

    # Existing rosters
    cur.execute("SELECT * FROM roster ORDER BY created_at DESC")
    rosters_list = [dict(r) for r in cur.fetchall()]

    if request.method == "POST":
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        assignments_json = request.form.get("assignments")  # now a single JSON string

        if not start_date or not end_date:
            flash("Start and end dates are required.", "danger")
            return redirect(url_for("main.rosters"))

        pdf_filename = f"roster_{start_date}_{end_date}.pdf"
        pdf_path = os.path.join(ROSTERS_DIR, pdf_filename)

        cur.execute("INSERT INTO roster (start_date, end_date, pdf_file) VALUES (?, ?, ?)",
                    (start_date, end_date, pdf_filename))
        roster_id = cur.lastrowid

        assignments_data = json.loads(assignments_json)
        for a in assignments_data:
            cur.execute(
                "INSERT INTO roster_assignments (roster_id, employee_id, duty_date, shift, hours, note) VALUES (?, ?, ?, ?, ?, ?)",
                (roster_id, a["employee_id"], a["duty_date"], a.get("shift"), a.get("hours"), a.get("note"))
            )
        conn.commit()

        # Generate PDF
        generate_roster_pdf(pdf_path, "My Company", "General Department", start_date, end_date, roster_id)
        flash("Roster saved successfully!", "success")
        return redirect(url_for("main.rosters"))

    # Before returning template, fetch last roster for "load previous" feature
    cur.execute("SELECT * FROM roster ORDER BY created_at DESC LIMIT 5")
    recent_rosters = [dict(r) for r in cur.fetchall()]

    return render_template(
        "rosters.html",
        employees=employees,
        rosters=rosters_list,
        recent_rosters=recent_rosters
    )

def _parse_time_to_hours(start_str, end_str):
    """Return hours (float) between start_str and end_str (H:M or H:M:S). Handles overnight shifts."""
    if not start_str or not end_str:
        return 0.0
    fmts = ("%H:%M:%S", "%H:%M")
    def _parse(s):
        for f in fmts:
            try:
                return datetime.strptime(s, f)
            except Exception:
                pass
        return None
    t1 = _parse(start_str)
    t2 = _parse(end_str)
    if not t1 or not t2:
        return 0.0
    # Normalize date so differences work; handle overnight by adding a day when end <= start
    t1_dt = datetime(2000,1,1, t1.hour, t1.minute, t1.second)
    t2_dt = datetime(2000,1,1, t2.hour, t2.minute, t2.second)
    if t2_dt <= t1_dt:
        t2_dt += timedelta(days=1)
    delta = (t2_dt - t1_dt).total_seconds() / 3600.0
    # guard against floating noise
    return round(delta, 3)

def generate_roster_pdf(filepath, company, department, start, end, roster_id):
    """
    Robust roster PDF generator:
      - Detects which columns exist in roster_assignments
      - Uses start/end times if present (computes shift hours)
      - Falls back to 'hours' column when start/end absent
      - Produces duty table and a summary table with per-employee totals
    """
    conn = get_db()
    cur = conn.cursor()

    # find available columns in roster_assignments
    cur.execute("PRAGMA table_info('roster_assignments')")
    cols_info = cur.fetchall()
    cols = [c["name"] if isinstance(c, dict) else (c["name"] if hasattr(c, 'keys') else c[1]) for c in cols_info]
    # sqlite3.Row is returned by our get_db; safe extraction:
    # Build select list depending on available columns
    select_parts = ["ra.duty_date", "s.name AS employee", "ra.employee_id"]
    if "start" in cols:
        select_parts.append("ra.start AS start_time")
    elif "start_time" in cols:
        select_parts.append("ra.start_time AS start_time")
    if "end" in cols:
        select_parts.append("ra.end AS end_time")
    elif "end_time" in cols:
        select_parts.append("ra.end_time AS end_time")
    if "shift" in cols:
        select_parts.append("ra.shift")
    if "hours" in cols:
        select_parts.append("ra.hours")
    if "note" in cols:
        select_parts.append("ra.note")

    # Always include safe columns if present; join
    select_clause = ", ".join(select_parts)

    sql = f"""
        SELECT {select_clause}
        FROM roster_assignments ra
        JOIN staff s ON ra.employee_id = s.staff_id
        WHERE ra.roster_id = ?
        ORDER BY ra.duty_date, s.name
    """
    cur.execute(sql, (roster_id,))
    rows = cur.fetchall()

    # Build PDF
    doc = SimpleDocTemplate(filepath, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph(f"<b>{company}</b>", styles["Title"]))
    elements.append(Paragraph(f"Department: {department}", styles["Heading2"]))
    elements.append(Paragraph(f"Roster Period: {start} to {end}", styles["Normal"]))
    elements.append(Spacer(1, 0.2 * inch))

    # Table of duties
    table_data = [["Date", "Employee", "Start", "End", "Shift", "Hours", "Note"]]
    totals = {}  # employee -> total hours

    for r in rows:
        # r is sqlite3.Row. Use mapping access; check keys exist
        row_keys = r.keys() if hasattr(r, "keys") else []
        duty_date = r["duty_date"] if "duty_date" in row_keys else ""
        employee = r["employee"] if "employee" in row_keys else ""
        start_time = r["start_time"] if "start_time" in row_keys else ""
        end_time = r["end_time"] if "end_time" in row_keys else ""
        shift = r["shift"] if "shift" in row_keys else ""
        hours_col = r["hours"] if "hours" in row_keys else None
        note = r["note"] if "note" in row_keys else ""

        # compute hours
        computed_hours = 0.0
        if start_time and end_time:
            computed_hours = _parse_time_to_hours(start_time, end_time)
        else:
            if hours_col is not None and hours_col != "":
                try:
                    computed_hours = float(hours_col)
                except Exception:
                    computed_hours = 0.0

        # accumulate
        totals[employee] = totals.get(employee, 0.0) + (computed_hours or 0.0)

        # pretty display of hours
        hours_display = f"{computed_hours:.2f}" if (computed_hours is not None) else (str(hours_col) if hours_col is not None else "")

        table_data.append([duty_date, employee, start_time or "", end_time or "", shift or "", hours_display, note or ""])

    # Table style
    col_widths = [1.3 * inch, 1.6 * inch, 0.9 * inch, 0.9 * inch, 1.0 * inch, 0.8 * inch, 1.6 * inch]
    duty_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    duty_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4b4b4b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (2, 1), (5, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))
    elements.append(duty_table)
    elements.append(Spacer(1, 0.25 * inch))

    # Totals summary
    summary_data = [["Employee", "Total Hours"]]
    for emp, h in sorted(totals.items(), key=lambda x: x[0]):
        summary_data.append([emp, f"{h:.2f} h"])

    # If no duties exist, put a placeholder row
    if len(summary_data) == 1:
        summary_data.append(["(No duties)", "0.00 h"])

    summary_table = Table(summary_data, colWidths=[3.2 * inch, 1.2 * inch])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2f6f9f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))
    elements.append(Paragraph("Weekly Totals", styles["Heading3"]))
    elements.append(summary_table)

    # Ensure output dir exists
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    doc.build(elements)


# DOWNLOAD (force download)
@bp.route("/rosters/download/<filename>")
def download_roster(filename):
    # keep this for explicit download
    return send_from_directory(ROSTERS_DIR, filename, as_attachment=True)

# VIEW (inline preview) — use this URL for preview iframe
@bp.route("/rosters/view/<filename>")
def view_roster(filename):
    # as_attachment=False lets the browser render inline when it can (PDF)
    return send_from_directory(ROSTERS_DIR, filename, as_attachment=False)


# Load previous roster duties as JSON for client-side "use for new roster"
@bp.route("/rosters/load/<int:roster_id>")
def load_roster(roster_id):
    conn = get_db()
    cur = conn.cursor()
    # determine columns present
    cur.execute("PRAGMA table_info('roster_assignments')")
    cols_info = cur.fetchall()
    col_names = [c["name"] for c in cols_info]

    wants = ["employee_id", "duty_date"]
    if "start" in col_names:
        wants.append("start")
    elif "start_time" in col_names:
        wants.append("start_time")
    if "end" in col_names:
        wants.append("end")
    elif "end_time" in col_names:
        wants.append("end_time")
    if "note" in col_names:
        wants.append("note")
    # ensure unique and valid selection
    wants = [w for w in wants if w in col_names or w in ("employee_id", "duty_date")]

    if not wants:
        # fallback minimal
        cur.execute("SELECT employee_id, duty_date FROM roster_assignments WHERE roster_id = ?", (roster_id,))
    else:
        sql = f"SELECT {', '.join(wants)} FROM roster_assignments WHERE roster_id = ? ORDER BY duty_date"
        cur.execute(sql, (roster_id,))
    rows = cur.fetchall()
    # convert rows to list of dicts safely
    result = []
    for r in rows:
        d = {}
        for k in r.keys():
            d[k] = r[k]
        result.append(d)
    return jsonify(result)
# Send roster email (employees' emails)
def send_roster_email(assignments, pdf_path):
    msg = EmailMessage()
    msg["Subject"] = "Your Weekly Roster"
    msg["From"] = "manager@example.com"
    msg["To"] = ",".join([emp["email"] for emp in assignments if emp.get("email")])
    msg.set_content("Please find your weekly roster attached.")

    with open(pdf_path, "rb") as f:
        msg.add_attachment(f.read(), maintype="application", subtype="pdf", filename=os.path.basename(pdf_path))

    with smtplib.SMTP("localhost") as server:
        server.send_message(msg)


