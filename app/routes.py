"""
routes.py
----------
Main route definitions for the Flask Roster Management System.

Handles:
- Authentication (login/logout/change password)
- Dashboard summary
- Employee CRUD operations
- Roster creation & PDF generation
- PDF download & preview
- Email sending (for future integration)
"""

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    session, flash, send_from_directory, jsonify, current_app, send_file, make_response
)
import sqlite3
import os
import json
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from email.message import EmailMessage
import smtplib
from io import BytesIO

from .database import get_db

# -------------------------
# Config
# -------------------------
bp = Blueprint("main", __name__)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ROSTERS_DIR = os.path.join(BASE_DIR, "Rosters")
os.makedirs(ROSTERS_DIR, exist_ok=True)


# -------------------------
# Require login decorator
# -------------------------
@bp.before_request
def require_login():
    """Protect all routes except login and static assets."""
    if "manager_id" not in session and request.endpoint not in ("main.login", "main.static"):
        flash("Please log in to access this page.", "warning")
        return redirect(url_for("main.login"))


# -------------------------
# Authentication Routes
# -------------------------
@bp.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate manager user."""
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
    """Log out current manager."""
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.login"))


@bp.route("/change_password", methods=["GET", "POST"])
def change_password():
    """Allow manager to change their password."""
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
    """Manager dashboard with summary stats and today’s duties."""
    conn = get_db()
    cur = conn.cursor()

    # Employee count
    cur.execute("SELECT COUNT(*) FROM staff")
    employee_count = cur.fetchone()[0]

    # Most recent roster
    cur.execute("SELECT * FROM roster ORDER BY created_at DESC LIMIT 1")
    latest_roster = cur.fetchone()
    if latest_roster is None:
        latest_roster = {"start_date": "N/A", "end_date": "N/A"}

    # Today's duties
    today_str = date.today().strftime("%Y-%m-%d")
    cur.execute("""
        SELECT s.name, ra.shift, ra.hours, ra.note
        FROM roster_assignments ra
        JOIN staff s ON ra.employee_id = s.staff_id
        WHERE ra.duty_date = ?
        ORDER BY ra.shift
    """, (today_str,))
    today_duties = cur.fetchall()

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
@bp.route("/employees")
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
        email = request.form.get("email", "")
        phone = request.form.get("phone", "")
        max_hours = request.form.get("max_hours", "")
        # support either comma-separated list or checkboxes
        days_unavailable = ",".join(request.form.getlist("days_unavailable"))

        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO staff (name, email, phone_number, max_hours, days_unavailable)
            VALUES (?, ?, ?, ?, ?)
        """, (name, email, phone, max_hours, days_unavailable))
        conn.commit()

        flash("Employee added successfully", "success")
        return redirect(url_for("main.employees"))

    return render_template("employee_form.html", action="Add")


@bp.route("/employees/edit/<int:staff_id>", methods=["GET", "POST"])
def edit_employee(staff_id):
    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        name = request.form["name"]
        email = request.form.get("email", "")
        phone = request.form.get("phone", "")
        max_hours = request.form.get("max_hours", "")
        days_unavailable = ",".join(request.form.getlist("days_unavailable"))

        cur.execute("""
            UPDATE staff
            SET name=?, email=?, phone_number=?, max_hours=?, days_unavailable=?
            WHERE staff_id=?
        """, (name, email, phone, max_hours, days_unavailable, staff_id))
        conn.commit()
        flash("Employee updated successfully", "info")
        return redirect(url_for("main.employees"))

    cur.execute("SELECT * FROM staff WHERE staff_id=?", (staff_id,))
    employee = cur.fetchone()
    return render_template("employee_form.html", employee=employee, action="Edit")


@bp.route("/employees/delete/<int:staff_id>")
def delete_employee(staff_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM staff WHERE staff_id=?", (staff_id,))
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

    # --------------------------------
    # Fetch Employees
    # --------------------------------
    cur.execute("SELECT * FROM staff ORDER BY name ASC")
    employees = [dict(e) for e in cur.fetchall()]

    # --------------------------------
    # Fetch Existing Rosters
    # --------------------------------
    cur.execute("SELECT * FROM roster ORDER BY created_at DESC")
    rosters_list = [dict(r) for r in cur.fetchall()]

    # --------------------------------
    # Fetch Company Info
    # --------------------------------
    cur.execute("SELECT company_name, department_name FROM company_info LIMIT 1")
    company_info = cur.fetchone()
    current_company_name = company_info["company_name"] if company_info else "My Company"
    current_department_name = company_info["department_name"] if company_info else "General Department"

    # --------------------------------
    # POST: Create or Edit Roster
    # --------------------------------
    if request.method == "POST":
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        assignments_json = request.form.get("assignments", "[]")
        company_name = request.form.get("company_name", "").strip() or current_company_name
        department_name = request.form.get("department_name", "").strip() or current_department_name
        edit_roster_id = request.form.get("edit_roster_id")

            # --- Auto-calc end date if missing ---
        if start_date and not end_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
                end_date = (start_dt + timedelta(days=6)).strftime("%Y-%m-%d")
            except Exception:
                flash("Invalid start date format.", "danger")
                return redirect(url_for("main.rosters"))


        if not start_date or not end_date:
            flash("Start and end dates are required.", "danger")
            return redirect(url_for("main.rosters"))

        # --- Update Company Info if changed ---
        cur.execute("SELECT company_id, company_name, department_name FROM company_info LIMIT 1")
        row = cur.fetchone()
        if row:
            if (company_name != row["company_name"]) or (department_name != row["department_name"]):
                cur.execute(
                    "UPDATE company_info SET company_name=?, department_name=? WHERE company_id=?",
                    (company_name, department_name, row["company_id"])
                )
        else:
            cur.execute(
                "INSERT INTO company_info (company_name, department_name) VALUES (?, ?)",
                (company_name, department_name)
            )
        conn.commit()

        # --- PDF file name ---
        pdf_filename = f"roster_{start_date}_{end_date}.pdf"
        pdf_path = os.path.join(ROSTERS_DIR, pdf_filename)

        # --- EDIT MODE ---

        if edit_roster_id:
            # ensure it's an int
            roster_id = int(edit_roster_id)
            cur.execute("""
                UPDATE roster
                SET start_date=?, end_date=?, pdf_file=?, edited_on=datetime('now')
                WHERE roster_id=?
            """, (start_date, end_date, pdf_filename, roster_id))
            cur.execute("DELETE FROM roster_assignments WHERE roster_id=?", (roster_id,))
        else:
            # --- NEW ROSTER ---
            cur.execute("""
                INSERT INTO roster (start_date, end_date, pdf_file, created_at)
                VALUES (?, ?, ?, datetime('now'))
            """, (start_date, end_date, pdf_filename))
            roster_id = cur.lastrowid


        # --- Save Assignments ---
        try:
            assignments_data = json.loads(assignments_json)
        except Exception:
            assignments_data = []

        for a in assignments_data:
            cur.execute("""
                INSERT INTO roster_assignments
                (roster_id, employee_id, duty_date, shift, hours, note, start_time, end_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                roster_id,
                a.get("employee_id"),
                a.get("duty_date"),
                a.get("shift"),
                a.get("hours"),
                a.get("note"),
                a.get("start") or a.get("start_time"),
                a.get("end") or a.get("end_time")
            ))
        conn.commit()

        # --- Generate PDF ---
        generate_roster_pdf(pdf_path, company_name, department_name, start_date, end_date, roster_id)
        flash("Roster saved successfully!", "success")

        # Refresh lists
        cur.execute("SELECT * FROM roster ORDER BY created_at DESC LIMIT 5")
        recent_rosters = [dict(r) for r in cur.fetchall()]

        return render_template(
            "rosters.html",
            employees=employees,
            rosters=rosters_list,
            recent_rosters=recent_rosters,
            current_company_name=company_name,
            current_department_name=department_name,
            edit_roster=None,
            edit_assignments=[]
        )

    # --------------------------------
    # Handle Delete Roster
    # --------------------------------
    delete_id = request.args.get("delete_id")
    if delete_id:
        cur.execute("SELECT pdf_file FROM roster WHERE roster_id=?", (int(delete_id),))
        row = cur.fetchone()
        if row and row["pdf_file"]:
            pdf_path = os.path.join(ROSTERS_DIR, row["pdf_file"])
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
        cur.execute("DELETE FROM roster WHERE roster_id=?", (int(delete_id),))
        conn.commit()
        flash("Roster and PDF deleted successfully", "danger")
        return redirect(url_for("main.rosters"))

    # --------------------------------
    # Handle Edit Mode (Load into form)
    # --------------------------------
    edit_id = request.args.get("edit_id")
    edit_roster = None
    edit_assignments = []
    if edit_id:
        cur.execute("SELECT * FROM roster WHERE roster_id=?", (edit_id,))
        edit_roster = cur.fetchone()
        cur.execute("SELECT * FROM roster_assignments WHERE roster_id=? ORDER BY duty_date", (edit_id,))
        edit_assignments = [dict(a) for a in cur.fetchall()]

    # --------------------------------
    # Fetch Recent Rosters
    # --------------------------------
    cur.execute("SELECT * FROM roster ORDER BY created_at DESC LIMIT 5")
    recent_rosters = [dict(r) for r in cur.fetchall()]

    return render_template(
        "rosters.html",
        employees=employees,
        rosters=rosters_list,
        recent_rosters=recent_rosters,
        current_company_name=current_company_name,
        current_department_name=current_department_name,
        edit_roster=edit_roster,
        edit_assignments=edit_assignments
    )


# -------------------------
# Helper Functions
# -------------------------
def _parse_time_to_hours(start_str, end_str):
    """Compute float hours between two HH:MM times, handling overnight shifts."""
    if not start_str or not end_str:
        return 0.0
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            t1 = datetime.strptime(start_str, fmt)
            t2 = datetime.strptime(end_str, fmt)
            break
        except ValueError:
            continue
    else:
        return 0.0
    t1_dt = datetime(2000, 1, 1, t1.hour, t1.minute, t1.second)
    t2_dt = datetime(2000, 1, 1, t2.hour, t2.minute, t2.second)
    if t2_dt <= t1_dt:
        t2_dt += timedelta(days=1)
    return round((t2_dt - t1_dt).total_seconds() / 3600.0, 2)


def _daterange(start_date_str, end_date_str):
    """Return list of date strings (YYYY-MM-DD) inclusive."""
    s = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    e = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    days = []
    cur = s
    while cur <= e:
        days.append(cur.strftime("%Y-%m-%d"))
        cur += timedelta(days=1)
    return days

def generate_roster_pdf(filepath, company, department, start, end, roster_id):
    """
    Generate a clean black-and-white roster PDF matrix:
      - Columns: dates (start..end)
      - Rows: employees
      - Each cell: shift/time/note
      - Include Created on / Edited on metadata
      - Include total hours summary
      - Output: PDF file at 'filepath'
    """
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # --- Fetch Roster Metadata ---
    cur.execute("""
        SELECT created_at, edited_on, start_date, end_date
        FROM roster
        WHERE roster_id = ?
    """, (roster_id,))
    roster_meta = cur.fetchone()
    created_on = roster_meta["created_at"] if roster_meta and roster_meta["created_at"] else ""
    edited_on = roster_meta["edited_on"] if roster_meta and roster_meta["edited_on"] else ""

    # --- Fetch Staff List ---
    cur.execute("SELECT staff_id, name FROM staff ORDER BY name ASC")
    staff_rows = cur.fetchall()
    staff_list = [dict(row) for row in staff_rows]

    # --- Build Date Columns ---
    dates = _daterange(start, end)

    # --- Fetch Assignments ---
    cur.execute("""
        SELECT employee_id, duty_date, shift, hours, note, start_time, end_time
        FROM roster_assignments
        WHERE roster_id = ?
    """, (roster_id,))
    assign_rows = cur.fetchall()

    # --- Map Assignments {employee_id: {duty_date: [assignment,...]}} ---
    assignments_map = {}
    for a in assign_rows:
        emp = a["employee_id"]
        duty = a["duty_date"]
        assignments_map.setdefault(emp, {}).setdefault(duty, []).append(dict(a))

    # --- Build Table Header ---
    styles = getSampleStyleSheet()
    header = ["Employee"]
    for d in dates:
        dt = datetime.strptime(d, "%Y-%m-%d").date()
        header.append(f"{dt.strftime('%a')}\n{d}")
    table_data = [header]

    # --- Build Employee Rows ---
    for s in staff_list:
        row = [s["name"]]
        emp_map = assignments_map.get(s["staff_id"], {})
        for d in dates:
            cell_items = []
            assignments_for_day = emp_map.get(d, [])
            for asn in assignments_for_day:
                st = asn.get("start_time") or ""
                en = asn.get("end_time") or ""
                hours = asn.get("hours") or ""
                shift = asn.get("shift") or ""
                note = asn.get("note") or ""

                display = ""
                if st and en:
                    display = f"{st}-{en}"
                elif hours:
                    display = f"{hours}h"

                if shift:
                    display = f"{shift}: {display}" if display else shift
                if note:
                    display = f"{display} ({note})" if display else f"({note})"

                cell_items.append(display)

            row.append("\n".join(cell_items))
        table_data.append(row)

    # --- Totals Summary Table ---
    totals_section = [["Employee", "Total Hours"]]
    for s in staff_list:
        emp_total = 0.0
        emp_map = assignments_map.get(s["staff_id"], {})
        for d, a_list in emp_map.items():
            for asn in a_list:
                st = asn.get("start_time") or ""
                en = asn.get("end_time") or ""
                if st and en:
                    emp_total += _parse_time_to_hours(st, en)
                else:
                    try:
                        emp_total += float(asn.get("hours") or 0)
                    except Exception:
                        pass
        totals_section.append([s["name"], f"{emp_total:.2f}"])

    # --- PDF Layout Setup ---
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    doc = SimpleDocTemplate(filepath, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elements = []

    # --- Header Info ---
    elements.append(Paragraph(f"<b>{company}</b>", styles["Title"]))
    elements.append(Paragraph(f"Department: {department}", styles["Normal"]))
    elements.append(Paragraph(f"Roster Period: {start} — {end}", styles["Normal"]))
    if created_on:
        elements.append(Paragraph(f"Created on: {created_on}", styles["Normal"]))
    if edited_on:
        elements.append(Paragraph(f"Edited on: {edited_on}", styles["Normal"]))
    elements.append(Spacer(1, 0.15 * inch))

    # --- Main Table (Roster Matrix) ---
    page_width = A4[0] - doc.leftMargin - doc.rightMargin
    emp_col = 2.5 * inch
    remaining = page_width - emp_col
    date_col_width = max(0.6 * inch, remaining / max(len(dates), 1))
    col_widths = [emp_col] + [date_col_width] * len(dates)

    matrix_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    matrix_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 1), (-1, -1), "LEFT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    elements.append(matrix_table)
    elements.append(Spacer(1, 0.2 * inch))

    # --- Totals Table ---
    summary_table = Table(totals_section, colWidths=[3.5 * inch, 1.2 * inch])
    summary_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    elements.append(Paragraph("Weekly Totals", styles["Heading3"]))
    elements.append(summary_table)

    # --- Build PDF ---
    doc.build(elements)

    #conn.close()


# -------------------------
# PDF Routes
# -------------------------
@bp.route("/rosters/download/<filename>")
def download_roster(filename):
    """Serve PDF inline so preview iframe can display it."""
    path = os.path.join(ROSTERS_DIR, filename)
    if not os.path.exists(path):
        return "Not found", 404
    # Use send_file with explicit inline content-disposition
    response = make_response(send_file(path, mimetype="application/pdf"))
    response.headers["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


@bp.route("/rosters/view/<filename>")
def view_roster(filename):
    """Backward-compatible view route (also inline)."""
    return download_roster(filename)


# -------------------------
# Load roster as JSON
# -------------------------
@bp.route("/rosters/load/<int:roster_id>")
def load_roster(roster_id):
    """
    Return JSON that the client expects. To help the frontend auto-populate the start/end
    and the assignment rows, we:
      - return an array where the first element is a meta object with start_date/end_date
      - subsequent elements are assignment objects with keys: employee_id, duty_date, start, end, shift, hours, note
    This keeps existing client-side iteration but also provides metadata.
    """
    conn = get_db()
    cur = conn.cursor()

    # roster meta
    cur.execute("SELECT roster_id, start_date, end_date, created_at, edited_on FROM roster WHERE roster_id = ?", (roster_id,))
    meta = cur.fetchone()
    meta_obj = {}
    if meta:
        meta_obj = {
            "meta": {
                "roster_id": meta["roster_id"],
                "start_date": meta["start_date"],
                "end_date": meta["end_date"],
                "created_at": meta["created_at"],
                "edited_on": meta["edited_on"],
            }
        }

    cur.execute("""
        SELECT employee_id, duty_date, shift, hours, note, start_time, end_time
        FROM roster_assignments
        WHERE roster_id = ?
        ORDER BY duty_date
    """, (roster_id,))
    rows = cur.fetchall()

    result = []
    if meta_obj:
        result.append(meta_obj)

    for r in rows:
        result.append({
            "employee_id": r["employee_id"],
            "duty_date": r["duty_date"],
            # return keys as frontend expects ('start' and 'end')
            "start": r["start_time"],
            "end": r["end_time"],
            "shift": r["shift"],
            "hours": r["hours"],
            "note": r["note"],
        })

    return jsonify(result)


# -------------------------
# Email (Optional)
# -------------------------
def send_roster_email(assignments, pdf_path):
    msg = EmailMessage()
    msg["Subject"] = "Your Weekly Roster"
    msg["From"] = "manager@example.com"
    msg["To"] = ",".join([a["email"] for a in assignments if a.get("email")])
    msg.set_content("Please find your weekly roster attached.")
    with open(pdf_path, "rb") as f:
        msg.add_attachment(f.read(), maintype="application", subtype="pdf", filename=os.path.basename(pdf_path))
    with smtplib.SMTP("localhost") as server:
        server.send_message(msg)
