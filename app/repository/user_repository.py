# User Repository
# Handles data access for user accounts (parents, teachers, admin).

from app.utils import get_cursor


def get_user_by_email(email):
    with get_cursor() as cursor:
        cursor.execute("SELECT * FROM Users WHERE email = %s;", (email.strip().lower(),))
        return cursor.fetchone()


def get_user_by_id(user_id):
    with get_cursor() as cursor:
        cursor.execute("SELECT * FROM Users WHERE user_id = %s;", (user_id,))
        return cursor.fetchone()


def create_pending_signup(role, full_name, email, password_hash, centre_id, classroom=None):
    """Creates a new self-registered account with status='pending'. The
    account cannot log in until an admin approves it (see approve_user)."""
    with get_cursor() as cursor:
        cursor.execute(
            """INSERT INTO Users (role, full_name, email, password_hash, classroom, centre_id, status)
               VALUES (%s, %s, %s, %s, %s, %s, 'pending')
               RETURNING user_id;""",
            (role, full_name, email.strip().lower(), password_hash, classroom, centre_id)
        )
        return cursor.fetchone()['user_id']


def list_pending_signups():
    with get_cursor() as cursor:
        cursor.execute(
            """SELECT u.user_id, u.role, u.full_name, u.email, u.classroom, u.created_at, c.name AS centre_name
               FROM Users u LEFT JOIN Centres c ON c.centre_id = u.centre_id
               WHERE u.status = 'pending'
               ORDER BY u.created_at ASC;"""
        )
        return cursor.fetchall()


def approve_user(user_id):
    with get_cursor() as cursor:
        cursor.execute(
            "UPDATE Users SET status = 'approved' WHERE user_id = %s AND status = 'pending';",
            (user_id,)
        )


def reject_user(user_id):
    with get_cursor() as cursor:
        cursor.execute(
            "UPDATE Users SET status = 'rejected' WHERE user_id = %s AND status = 'pending';",
            (user_id,)
        )


def list_admin_user_ids():
    with get_cursor() as cursor:
        cursor.execute("SELECT user_id FROM Users WHERE role = 'Admin' AND status = 'approved';")
        return [row['user_id'] for row in cursor.fetchall()]

