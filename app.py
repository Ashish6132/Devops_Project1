from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = "change-this-to-a-secure-secret-key"

DATABASE = "complaints.db"


# Database Connection
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# Create Database Table
def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT DEFAULT 'Pending',
                date TEXT NOT NULL
            )
        """)
        conn.commit()


# Login Required
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "student_id" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# Home Page
@app.route("/")
def home():
    return render_template("index.html")


# Login Page
@app.route("/login", methods=["GET"])
def login():
    return render_template("login.html")


# Student Dashboard
@app.route("/dashboard")
@login_required
def dashboard():

    student_id = session["student_id"]
    student_name = session.get("student_name", "Student")

    with get_db() as conn:
        complaints = conn.execute("""
            SELECT * FROM complaints
            WHERE student_id = ?
            ORDER BY id DESC
        """, (student_id,)).fetchall()

    total_complaints = len(complaints)

    pending = sum(
        1 for c in complaints
        if c["status"] == "Pending"
    )

    in_progress = sum(
        1 for c in complaints
        if c["status"] == "In Progress"
    )

    resolved = sum(
        1 for c in complaints
        if c["status"] == "Resolved"
    )

    return render_template(
        "dashboard.html",
        student_name=student_name,
        complaints=complaints,
        total_complaints=total_complaints,
        pending=pending,
        in_progress=in_progress,
        resolved=resolved
    )


# Submit Complaint
@app.route("/submit_complaint", methods=["POST"])
@login_required
def submit_complaint():

    title = request.form.get("title", "").strip()
    category = request.form.get("category", "").strip()
    description = request.form.get(
        "description", ""
    ).strip()

    if not title or not category or not description:
        flash("All fields are required.", "danger")
        return redirect(url_for("dashboard"))

    student_id = session["student_id"]
    date = datetime.now().strftime("%Y-%m-%d")

    with get_db() as conn:
        conn.execute("""
            INSERT INTO complaints
            (student_id, title, category,
             description, status, date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            student_id,
            title,
            category,
            description,
            "Pending",
            date
        ))
        conn.commit()

    flash("Complaint submitted successfully!", "success")

    return redirect(url_for("dashboard"))


# Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)