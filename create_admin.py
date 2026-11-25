import sqlite3
from getpass import getpass

from werkzeug.security import generate_password_hash
from app import DATABASE, init_db


def create_admin():
    init_db()

    print("\n=== Create Admin Account ===")

    name = input("Admin Name: ").strip()
    email = input("Admin Email: ").strip().lower()
    password = getpass("Admin Password: ")
    confirm = getpass("Confirm Password: ")

    if not name or "@" not in email:
        print("Invalid name or email.")
        return

    if len(password) < 12:
        print("Password must contain at least 12 characters.")
        return

    if password != confirm:
        print("Passwords do not match.")
        return

    conn = sqlite3.connect(DATABASE)

    try:
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if existing:
            print("Email already registered. Use a different email.")
            return

        hashed_password = generate_password_hash(password)

        conn.execute("""
            INSERT INTO users (name, email, password, role)
            VALUES (?, ?, ?, 'admin')
        """, (name, email, hashed_password))

        conn.commit()
        print("Admin account created successfully!")

    except sqlite3.Error as error:
        print("Database error:", error)

    finally:
        conn.close()


if __name__ == "__main__":
    create_admin()