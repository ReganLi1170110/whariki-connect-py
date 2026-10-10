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


def set_reset_token(user_id, token, expires_at):
    with get_cursor() as cursor:
        cursor.execute(
            "UPDATE Users SET reset_token = %s, reset_token_expires = %s WHERE user_id = %s;",
            (token, expires_at, user_id)
        )


def get_user_by_reset_token(token):
    """Only returns the user if the token exists AND hasn't expired - an
    expired or unknown token is treated the same as no user found, so the
    route can't be used to tell a caller which tokens are 'real'."""
    with get_cursor() as cursor:
        cursor.execute(
            """SELECT * FROM Users
               WHERE reset_token = %s AND reset_token_expires > now();""",
            (token,)
        )
        return cursor.fetchone()


def clear_reset_token(user_id):
    with get_cursor() as cursor:
        cursor.execute(
            "UPDATE Users SET reset_token = NULL, reset_token_expires = NULL WHERE user_id = %s;",
            (user_id,)
        )


def update_password(user_id, password_hash):
    with get_cursor() as cursor:
        cursor.execute(
            "UPDATE Users SET password_hash = %s WHERE user_id = %s;",
            (password_hash, user_id)
        )


def suspend_user(user_id):
    """Deactivates an approved account (e.g. staff left) without deleting
    it - their history (learning stories written, messages sent, etc.)
    stays intact, they just can't log in any more. Only ever moves an
    approved account to suspended, never touches pending/rejected."""
    with get_cursor() as cursor:
        cursor.execute(
            "UPDATE Users SET status = 'suspended' WHERE user_id = %s AND status = 'approved';",
            (user_id,)
        )


def reactivate_user(user_id):
    with get_cursor() as cursor:
        cursor.execute(
            "UPDATE Users SET status = 'approved' WHERE user_id = %s AND status = 'suspended';",
            (user_id,)
        )


def update_classroom(user_id, classroom):
    """Reassigns a teacher to a different room. Only meaningful for
    Teacher accounts - the caller is responsible for that check, since a
    Parent/Admin's classroom column is unused by design."""
    with get_cursor() as cursor:
        cursor.execute(
            "UPDATE Users SET classroom = %s WHERE user_id = %s AND role = 'Teacher';",
            (classroom, user_id)
        )

