import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import subprocess
import sys
import os
import calendar
import base64
import json
import csv
import cv2
import numpy as np
from database import get_connection
from flask import send_file
from openpyxl import Workbook
from datetime import date, datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

CASCADE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "haarcascade_frontalface_default.xml"
)


app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "ai_face_attendance_secret")


def get_filtered_attendance(register_number="", department="", date_from="", date_to=""):
    db = get_connection()
    cursor = db.cursor(dictionary=True)

    query = """
        SELECT
            a.register_number AS register_number,
            s.student_name AS student_name,
            s.department AS department,
            a.attendance_date AS attendance_date,
            a.attendance_time AS attendance_time
        FROM attendance a
        LEFT JOIN students s
            ON a.register_number = s.register_number
        WHERE 1=1
    """

    params = []

    if register_number:
        query += " AND a.register_number LIKE %s"
        params.append(f"%{register_number}%")

    if department:
        query += " AND s.department = %s"
        params.append(department)

    if date_from:
        query += " AND a.attendance_date >= %s"
        params.append(date_from)

    if date_to:
        query += " AND a.attendance_date <= %s"
        params.append(date_to)

    query += " ORDER BY a.attendance_date DESC, a.attendance_time DESC"

    cursor.execute(query, tuple(params))
    data = cursor.fetchall()

    cursor.close()
    db.close()

    return data


def get_date_range_for_report_type(report_type):
    today = date.today()

    if report_type == "daily":
        d = today.strftime("%Y-%m-%d")
        return d, d

    if report_type == "monthly":
        first_day = today.replace(day=1).strftime("%Y-%m-%d")
        last_day_num = calendar.monthrange(today.year, today.month)[1]
        last_day = today.replace(day=last_day_num).strftime("%Y-%m-%d")
        return first_day, last_day

    return "", ""


@app.route("/")
def root():
    return redirect(url_for("dashboard"))

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin123":
            session["user"] = username
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Invalid username or password")

    return render_template("login.html")
@app.route("/export_excel")
def export_excel():

    if "user" not in session:
        return redirect(url_for("login"))

    report_type = request.args.get("report_type", "")
    register_number = request.args.get("register_number", "").strip()
    department = request.args.get("department", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    if report_type in ("daily", "monthly"):
        date_from, date_to = get_date_range_for_report_type(report_type)

    data = get_filtered_attendance(register_number, department, date_from, date_to)

    wb = Workbook()
    ws = wb.active
    ws.title = "Attendance"

    ws.append(["Register Number", "Student Name", "Department", "Date", "Time"])

    for row in data:
        ws.append([
            row["register_number"],
            row["student_name"] or "",
            row["department"] or "",
            str(row["attendance_date"]),
            str(row["attendance_time"]),
        ])

    filename = "Attendance_Report.xlsx"
    wb.save(filename)

    return send_file(filename, as_attachment=True)


@app.route("/export_pdf")
def export_pdf():

    if "user" not in session:
        return redirect(url_for("login"))

    report_type = request.args.get("report_type", "")
    register_number = request.args.get("register_number", "").strip()
    department = request.args.get("department", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    if report_type in ("daily", "monthly"):
        date_from, date_to = get_date_range_for_report_type(report_type)

    data = get_filtered_attendance(register_number, department, date_from, date_to)

    filename = "Attendance_Report.pdf"
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title_text = "Attendance Report"
    if report_type == "daily":
        title_text = f"Daily Attendance Report - {date.today().strftime('%Y-%m-%d')}"
    elif report_type == "monthly":
        title_text = f"Monthly Attendance Report - {date.today().strftime('%B %Y')}"

    story.append(Paragraph(title_text, styles["Title"]))
    story.append(Spacer(1, 12))

    filter_bits = []
    if register_number:
        filter_bits.append(f"Register Number contains: {register_number}")
    if department:
        filter_bits.append(f"Department: {department}")
    if date_from or date_to:
        filter_bits.append(f"Date range: {date_from or 'start'} to {date_to or 'today'}")

    if filter_bits:
        story.append(Paragraph(" | ".join(filter_bits), styles["Normal"]))
        story.append(Spacer(1, 12))

    table_data = [["Register Number", "Student Name", "Department", "Date", "Time"]]

    for row in data:
        table_data.append([
            row["register_number"],
            row["student_name"] or "-",
            row["department"] or "-",
            str(row["attendance_date"]),
            str(row["attendance_time"]),
        ])

    if len(table_data) == 1:
        story.append(Paragraph("No attendance records found for the selected filters.", styles["Normal"]))
    else:
        pdf_table = Table(table_data, repeatRows=1)
        pdf_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f7f7")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(pdf_table)

    doc.build(story)

    return send_file(filename, as_attachment=True)


@app.route("/reports")
def reports():

    if "user" not in session:
        return redirect(url_for("login"))

    db = get_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT DISTINCT department FROM students ORDER BY department")
    departments = [row["department"] for row in cursor.fetchall()]
    cursor.close()
    db.close()

    return render_template("reports.html", departments=departments)
@app.route("/register", methods=["GET", "POST"])
def register():

    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        student_name = request.form["student_name"]
        register_number = request.form["register_number"]
        department = request.form["department"]
        year = request.form["year"]

        db = get_connection()
        cursor = db.cursor()

        cursor.execute("""
            INSERT INTO students
            (student_name, register_number, department, year)
            VALUES (%s, %s, %s, %s)
        """, (student_name, register_number, department, year))

        db.commit()

        cursor.close()
        db.close()

        return redirect(url_for("capture_face_page", register_number=register_number))

    return render_template("register.html")
@app.route("/delete_student/<register_number>")
def delete_student(register_number):

    if "user" not in session:
        return redirect(url_for("login"))

    db = get_connection()
    cursor = db.cursor()

    cursor.execute(
        "DELETE FROM students WHERE register_number=%s",
        (register_number,)
    )

    db.commit()

    cursor.close()
    db.close()

    return redirect(url_for("students"))


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/home")
def home():

    if "user" not in session:
        return redirect(url_for("login"))

    return render_template("index.html")


@app.route("/capture_face_page")
def capture_face_page():

    if "user" not in session:
        return redirect(url_for("login"))

    register_number = request.args.get("register_number", "")

    return render_template("capture_face.html", register_number=register_number)


@app.route("/api/save_face_image", methods=["POST"])
def save_face_image():

    if "user" not in session:
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    register_number = data.get("register_number")
    image_b64 = data.get("image")

    if not register_number or not image_b64:
        return jsonify({"error": "missing register_number or image"}), 400

    try:
        _, encoded = image_b64.split(",", 1) if "," in image_b64 else (None, image_b64)
        img_bytes = base64.b64decode(encoded)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({"error": "could not decode image"}), 400

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        detector = cv2.CascadeClassifier(CASCADE_PATH)
        faces = detector.detectMultiScale(gray, 1.3, 5, minSize=(100, 100))

        if len(faces) == 0:
            return jsonify({"status": "no_face"})

        x, y, w, h = faces[0]
        face_crop = gray[y:y + h, x:x + w]

        folder = os.path.join("dataset", register_number)
        os.makedirs(folder, exist_ok=True)

        count = len(os.listdir(folder)) + 1
        cv2.imwrite(os.path.join(folder, f"{count}.jpg"), face_crop)

        return jsonify({"status": "saved", "count": count})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/train")
def train():

    if "user" not in session:
        return redirect(url_for("login"))

    result = subprocess.run(
        [sys.executable, "train_model.py"],
        text=True,
        capture_output=True
    )

    print(result.stdout)
    print(result.stderr)

    if result.returncode != 0:
        return (
            "<h2>\u274c Training Failed</h2>"
            f"<pre>{result.stdout}\n{result.stderr}</pre>"
            f'<p><a href="{url_for("dashboard")}">Back to Dashboard</a></p>'
        )

    return (
        "<h2>\u2705 Training Completed</h2>"
        f"<pre>{result.stdout}</pre>"
        f'<p><a href="{url_for("dashboard")}">Back to Dashboard</a></p>'
    )


@app.route("/take_attendance", methods=["POST"])
def take_attendance():

    if "user" not in session:
        return redirect(url_for("login"))

    register_number = request.form["register_number"]

    return redirect(url_for("verify_attendance_page", register_number=register_number))


@app.route("/verify_attendance_page")
def verify_attendance_page():

    if "user" not in session:
        return redirect(url_for("login"))

    register_number = request.args.get("register_number", "")

    return render_template("verify_attendance.html", register_number=register_number)


@app.route("/api/verify_face", methods=["POST"])
def verify_face():

    if "user" not in session:
