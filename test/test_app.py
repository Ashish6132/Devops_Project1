import sys
import sqlite3
from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

# Import app.py from the project root
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app as project


# ============ TEST SETUP ============

@pytest.fixture
def client(tmp_path, monkeypatch):

    # Temporary test database
    test_db = tmp_path / "test_complaints.db"

    monkeypatch.setattr(
        project,
        "DATABASE",
        str(test_db)
    )

    project.app.config.update(
        TESTING=True,
        SECRET_KEY="testing-secret-key"
    )

    # Create database tables
    project.init_db()

    with project.app.test_client() as client:
        yield client


# ============ HELPER FUNCTIONS ============

def create_user(email, password, role="student"):

    with project.get_db() as conn:
        conn.execute("""
            INSERT INTO users
            (name, email, password, role)
            VALUES (?, ?, ?, ?)
        """, (
            "Test User",
            email,
            generate_password_hash(password),
            role
        ))


def login(client, email, password):

    return client.post(
        "/login",
        data={
            "email": email,
            "password": password
        },
        follow_redirects=False
    )


# ============ TEST 1: HOME PAGE ============

def test_home_page(client):

    response = client.get("/")

    assert response.status_code == 200


# ============ TEST 2: REGISTRATION ============

def test_student_registration(client):

    response = client.post(
        "/register",
        data={
            "name": "Rahul",
            "email": "rahul@example.com",
            "password": "Student@12345"
        },
        follow_redirects=False
    )

    assert response.status_code == 302

    with project.get_db() as conn:
        user = conn.execute("""
            SELECT * FROM users
            WHERE email = ?
        """, ("rahul@example.com",)).fetchone()

    assert user is not None
    assert user["role"] == "student"
    assert user["password"] != "Student@12345"


# ============ TEST 3: STUDENT LOGIN ============

def test_student_login(client):

    create_user(
        "student@example.com",
        "Student@12345"
    )

    response = login(
        client,
        "student@example.com",
        "Student@12345"
    )

    assert response.status_code == 302
    assert "/dashboard" in response.location


# ============ TEST 4: INVALID LOGIN ============

def test_invalid_login(client):

    response = login(
        client,
        "wrong@example.com",
        "WrongPassword"
    )

    assert response.status_code == 200


# ============ TEST 5: DASHBOARD PROTECTION ============

def test_dashboard_requires_login(client):

    response = client.get("/dashboard")

    assert response.status_code == 302
    assert "/login" in response.location


# ============ TEST 6: STUDENT DASHBOARD ============

def test_student_dashboard(client):

    create_user(
        "student@example.com",
        "Student@12345"
    )

    login(
        client,
        "student@example.com",
        "Student@12345"
    )

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert b"Welcome" in response.data


# ============ TEST 7: COMPLAINT SUBMISSION ============

def test_submit_complaint(client):

    create_user(
        "student@example.com",
        "Student@12345"
    )

    login(
        client,
        "student@example.com",
        "Student@12345"
    )

    response = client.post(
        "/complaints",
        data={
            "title": "Library WiFi Problem",
            "category": "Library",
            "description": "WiFi is not working."
        },
        follow_redirects=False
    )

    assert response.status_code == 302

    with project.get_db() as conn:
        complaint = conn.execute("""
            SELECT * FROM complaints
            WHERE title = ?
        """, ("Library WiFi Problem",)).fetchone()

    assert complaint is not None
    assert complaint["status"] == "Pending"


# ============ TEST 8: COMPLAINT TRACKING ============

def test_complaint_tracking(client):

    create_user(
        "student@example.com",
        "Student@12345"
    )

    login(
        client,
        "student@example.com",
        "Student@12345"
    )

    response = client.get("/complaint-status")

    assert response.status_code == 200


# ============ TEST 9: ADMIN LOGIN ============

def test_admin_login(client):

    create_user(
        "admin@example.com",
        "Admin@123456789",
        role="admin"
    )

    response = login(
        client,
        "admin@example.com",
        "Admin@123456789"
    )

    assert response.status_code == 302
    assert "/admin" in response.location


# ============ TEST 10: ADMIN DASHBOARD ============

def test_admin_dashboard(client):

    create_user(
        "admin@example.com",
        "Admin@123456789",
        role="admin"
    )

    login(
        client,
        "admin@example.com",
        "Admin@123456789"
    )

    response = client.get("/admin")

    assert response.status_code == 200


# ============ TEST 11: ADMIN ACCESS CONTROL ============

def test_student_cannot_access_admin(client):

    create_user(
        "student@example.com",
        "Student@12345"
    )

    login(
        client,
        "student@example.com",
        "Student@12345"
    )

    response = client.get("/admin")

    assert response.status_code == 302


# ============ TEST 12: STATUS UPDATE ============

def test_admin_updates_status(client):

    create_user(
        "student@example.com",
        "Student@12345"
    )

    create_user(
        "admin@example.com",
        "Admin@123456789",
        role="admin"
    )

    with project.get_db() as conn:

        student = conn.execute("""
            SELECT id FROM users
            WHERE email = ?
        """, ("student@example.com",)).fetchone()

        cursor = conn.execute("""
            INSERT INTO complaints
            (
                user_id,
                title,
                category,
                description,
                status
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            student["id"],
            "Test Complaint",
            "Academic",
            "Test description",
            "Pending"
        ))

        complaint_id = cursor.lastrowid

    login(
        client,
        "admin@example.com",
        "Admin@123456789"
    )

    response = client.post(
        f"/update-status/{complaint_id}",
        data={
            "status": "Resolved"
        },
        follow_redirects=False
    )

    assert response.status_code == 302

    with project.get_db() as conn:
        complaint = conn.execute("""
            SELECT status FROM complaints
            WHERE id = ?
        """, (complaint_id,)).fetchone()

    assert complaint["status"] == "Resolved"


# ============ TEST 13: LOGOUT ============

def test_logout(client):

    create_user(
        "student@example.com",
        "Student@12345"
    )

    login(
        client,
        "student@example.com",
        "Student@12345"
    )

    response = client.get("/logout")

    assert response.status_code == 302

    protected = client.get("/dashboard")

    assert protected.status_code == 302
    assert "/login" in protected.location