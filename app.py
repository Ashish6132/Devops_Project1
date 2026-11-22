import os
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash
)
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY", "development-only-change-me"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "complaints.db")


# Database connection
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# Initialize database
def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'student'
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending',
                date TEXT NOT NULL,
                FOREIGN KEY (student_id)
                    REFERENCES users(id)
            )
        """)

        conn.commit()


# Login protection
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "student_id" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


# Admin protection
def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            return "Access denied", 403
        return f(*args, **kwargs)
    return wrapper


# Home page
@app.route("/")
@app.route("/home")
def home():
    return render_template("index.html")


# Registration
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get(
            "email", ""
        ).strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash(
                "Password must contain at least 8 characters.",
                "danger"
            )
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        try:
            with get_db() as conn:
                conn.execute("""
                    INSERT INTO users
                    (name, email, password, role)
                    VALUES (?, ?, ?, ?)
                """, (
                    name, email, hashed_password, "student"
                ))
                conn.commit()

        except sqlite3.IntegrityError:
            flash("Email already registered.", "danger")
            return redirect(url_for("register"))

        flash("Registration successful!", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get(
            "email", ""
        ).strip().lower()
        password = request.form.get("password", "")

        with get_db() as conn:
            user = conn.execute("""
                SELECT * FROM users
                WHERE email = ?
            """, (email,)).fetchone()

        if user and check_password_hash(
            user["password"], password
        ):
            session.clear()
            session["student_id"] = user["id"]
            session["student_name"] = user["name"]
            session["role"] = user["role"]

            if user["role"] == "admin":
                return redirect(url_for("admin"))

            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


# Student dashboard
@app.route("/dashboard")
@login_required
def dashboard():
    if session.get("role") != "student":
        return redirect(url_for("admin"))

    with get_db() as conn:
        complaints = conn.execute("""
            SELECT * FROM complaints
            WHERE student_id = ?
            ORDER BY id DESC
        """, (session["student_id"],)).fetchall()

    return render_template(
        "dashboard.html",
        student_name=session["student_name"],
        complaints=complaints,
        total_complaints=len(complaints),
        pending=sum(
            c["status"] == "Pending"
            for c in complaints
        ),
        in_progress=sum(
            c["status"] == "In Progress"
            for c in complaints
        ),
        resolved=sum(
            c["status"] == "Resolved"
            for c in complaints
        )
    )


# Submit complaint
@app.route("/submit_complaint", methods=["POST"])
@login_required
def submit_complaint():
    if session.get("role") != "student":
        return "Access denied", 403

    title = request.form.get("title", "").strip()
    category = request.form.get("category", "").strip()
    description = request.form.get(
        "description", ""
    ).strip()

    if not title or not category or not description:
        flash("All fields are required.", "danger")
        return redirect(url_for("dashboard"))

    with get_db() as conn:
        conn.execute("""
            INSERT INTO complaints
            (student_id, title, category,
             description, status, date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            session["student_id"],
            title,
            category,
            description,
            "Pending",
            datetime.now().strftime("%Y-%m-%d")
        ))
        conn.commit()

    flash("Complaint submitted successfully!", "success")
    return redirect(url_for("dashboard"))


# Admin dashboard
@app.route("/admin")
@login_required
@admin_required
def admin():
    with get_db() as conn:
        complaints = conn.execute("""
            SELECT * FROM complaints
            ORDER BY id DESC
        """).fetchall()

    return render_template(
        "admin.html",
        complaints=complaints,
        total_complaints=len(complaints),
        pending=sum(
            c["status"] == "Pending"
            for c in complaints
        ),
        in_progress=sum(
            c["status"] == "In Progress"
            for c in complaints
        ),
        resolved=sum(
            c["status"] == "Resolved"
            for c in complaints
        )
    )


# Update complaint status
@app.route(
    "/update_status/<int:complaint_id>",
    methods=["POST"]
)
@login_required
@admin_required
def update_status(complaint_id):
    status = request.form.get("status")

    allowed = ["Pending", "In Progress", "Resolved"]

    if status not in allowed:
        return "Invalid status", 400

    with get_db() as conn:
        result = conn.execute("""
            UPDATE complaints
            SET status = ?
            WHERE id = ?
        """, (status, complaint_id))
        conn.commit()

    if result.rowcount == 0:
        return "Complaint not found", 404

    flash("Complaint status updated!", "success")
    return redirect(url_for("admin"))


# Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# Start application
init_db()

if __name__ == "__main__":
    app.run(debug=True)