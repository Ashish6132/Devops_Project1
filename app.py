import os
import sqlite3
from functools import wraps

from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)


# =============== FLASK SETUP ===============

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "development-key-change-me"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "complaints.db")


# =============== DATABASE ===============

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


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
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)


# =============== AUTHENTICATION ===============

def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.")
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return wrapper


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if (
            "user_id" not in session
            or session.get("role") != "admin"
        ):
            flash("Admin access required.")
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return wrapper


# =============== HOME ===============

@app.route("/")
def home():
    return render_template("index.html")


# =============== REGISTER ===============

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or len(password) < 8:
            flash(
                "Enter valid details and a password "
                "of at least 8 characters."
            )
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        try:
            with get_db() as conn:
                conn.execute("""
                    INSERT INTO users
                    (name, email, password, role)
                    VALUES (?, ?, ?, 'student')
                """, (
                    name,
                    email,
                    hashed_password
                ))

            flash("Registration successful! Please login.")
            return redirect(url_for("login"))

        except sqlite3.IntegrityError:
            flash("Email already registered.")

    return render_template("register.html")


# =============== LOGIN ===============

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
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

            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]

            if user["role"] == "admin":
                return redirect(url_for("admin"))

            return redirect(url_for("dashboard"))

        flash("Invalid email or password.")

    return render_template("login.html")


# =============== STUDENT DASHBOARD ===============

@app.route("/dashboard")
@login_required
def dashboard():

    if session.get("role") == "admin":
        return redirect(url_for("admin"))

    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM complaints
            WHERE user_id = ?
            ORDER BY id DESC
        """, (session["user_id"],)).fetchall()

    complaints_list = [dict(row) for row in rows]

    total = len(complaints_list)

    pending = sum(
        1 for c in complaints_list
        if c["status"] == "Pending"
    )

    in_progress = sum(
        1 for c in complaints_list
        if c["status"] == "In Progress"
    )

    resolved = sum(
        1 for c in complaints_list
        if c["status"] == "Resolved"
    )

    return render_template(
        "dashboard.html",
        student_name=session.get("name"),
        complaints=complaints_list,
        total_complaints=total,
        pending=pending,
        in_progress=in_progress,
        resolved=resolved
    )


# =============== COMPLAINT SUBMISSION ===============

@app.route("/complaints", methods=["GET", "POST"])
@login_required
def complaints():

    if session.get("role") == "admin":
        return redirect(url_for("admin"))

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get(
            "description", ""
        ).strip()

        allowed_categories = {
            "Academic",
            "Hostel",
            "Library",
            "Infrastructure",
            "Transport",
            "Other"
        }

        if (
            not title
            or len(title) > 150
            or category not in allowed_categories
            or not description
            or len(description) > 3000
        ):
            flash("Please enter valid complaint details.")
            return redirect(url_for("complaints"))

        with get_db() as conn:
            conn.execute("""
                INSERT INTO complaints
                (
                    user_id,
                    title,
                    category,
                    description,
                    status
                )
                VALUES (?, ?, ?, ?, 'Pending')
            """, (
                session["user_id"],
                title,
                category,
                description
            ))

        flash("Complaint submitted successfully!")
        return redirect(url_for("complaints"))

    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM complaints
            WHERE user_id = ?
            ORDER BY id DESC
        """, (session["user_id"],)).fetchall()

    return render_template(
        "complaints.html",
        complaints=[dict(row) for row in rows]
    )


# =============== COMPLAINT STATUS ===============

@app.route("/complaint-status")
@login_required
def complaint_status():

    if session.get("role") == "admin":
        return redirect(url_for("admin"))

    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                id,
                title,
                category,
                description,
                status,
                created_at
            FROM complaints
            WHERE user_id = ?
            ORDER BY id DESC
        """, (session["user_id"],)).fetchall()

    complaints_list = [dict(row) for row in rows]

    total = len(complaints_list)

    pending = sum(
        1 for c in complaints_list
        if c["status"] == "Pending"
    )

    in_progress = sum(
        1 for c in complaints_list
        if c["status"] == "In Progress"
    )

    resolved = sum(
        1 for c in complaints_list
        if c["status"] == "Resolved"
    )

    return render_template(
        "complaint_status.html",
        complaints=complaints_list,
        total_complaints=total,
        pending=pending,
        in_progress=in_progress,
        resolved=resolved
    )


# =============== ADMIN DASHBOARD ===============

@app.route("/admin")
@admin_required
def admin():

    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                complaints.*,
                users.name AS student_name,
                users.email AS student_email
            FROM complaints
            JOIN users
            ON complaints.user_id = users.id
            ORDER BY complaints.id DESC
        """).fetchall()

    complaints_list = [dict(row) for row in rows]

    total = len(complaints_list)

    pending = sum(
        1 for c in complaints_list
        if c["status"] == "Pending"
    )

    in_progress = sum(
        1 for c in complaints_list
        if c["status"] == "In Progress"
    )

    resolved = sum(
        1 for c in complaints_list
        if c["status"] == "Resolved"
    )

    return render_template(
        "admin.html",
        complaints=complaints_list,
        total_complaints=total,
        pending=pending,
        in_progress=in_progress,
        resolved=resolved
    )


# =============== UPDATE STATUS ===============

@app.route(
    "/update-status/<int:complaint_id>",
    methods=["POST"]
)
@admin_required
def update_status(complaint_id):

    status = request.form.get("status", "")

    allowed_statuses = {
        "Pending",
        "In Progress",
        "Resolved"
    }

    if status not in allowed_statuses:
        flash("Invalid complaint status.")
        return redirect(url_for("admin"))

    with get_db() as conn:
        result = conn.execute("""
            UPDATE complaints
            SET status = ?
            WHERE id = ?
        """, (status, complaint_id))

    if result.rowcount == 0:
        flash("Complaint not found.")
    else:
        flash("Complaint status updated!")

    return redirect(url_for("admin"))


# =============== LOGOUT ===============

@app.route("/logout")
@login_required
def logout():

    session.clear()
    flash("Logged out successfully.")

    return redirect(url_for("login"))


# =============== RUN APPLICATION ===============

if __name__ == "__main__":
    init_db()
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        use_reloader=False
    )