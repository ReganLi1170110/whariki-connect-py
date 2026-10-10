import re

from flask_bcrypt import Bcrypt
from flask import session, redirect, url_for, flash, request
from functools import wraps
from contextlib import contextmanager
from app import flask_app as app
from app.db import db

flask_bcrypt = Bcrypt(app)

# Minimum length is deliberately "more than 8" (i.e. 9+), not "8 or more" -
# combined with the uppercase/special-character rules below this is the one
# password policy used everywhere a password is set (signup, reset).
PASSWORD_MIN_LENGTH = 9
PASSWORD_SPECIAL_CHARS = r"!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?"
_PASSWORD_SPECIAL_RE = re.compile(f"[{PASSWORD_SPECIAL_CHARS}]")


def validate_password_strength(password):
    """Returns an error message if the password is too weak, otherwise None."""
    if len(password) <= 8:
        return f"Password must be more than 8 characters (at least {PASSWORD_MIN_LENGTH})."
    if not re.search(r"[A-Z]", password):
        return "Password must include at least one uppercase letter."
    if not _PASSWORD_SPECIAL_RE.search(password):
        return "Password must include at least one special character (e.g. ! @ # $ % &)."
    return None


def generate_password_hash(password):
    return flask_bcrypt.generate_password_hash(password).decode('utf-8')


def check_password_hash(password_hash, password):
    return flask_bcrypt.check_password_hash(password_hash, password)


def is_logged_in():
    return 'user_id' in session


def login_required(message="Please log in to access this page."):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'user_id' not in session:
                flash(message, "danger")
                return redirect(url_for("login"))
            return f(*args, **kwargs)
        return wrapper
    return decorator


def roles_required(*allowed_roles):
    """Restricts a route to one or more roles, e.g. @roles_required('Teacher', 'Admin')"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user_role = session.get("role")
            if user_role not in allowed_roles:
                flash("You do not have permission to view that page.", "danger")
                return redirect(url_for("overview"))
            return f(*args, **kwargs)
        return wrapper
    return decorator


def get_dashboard_link_for_role():
    if not is_logged_in():
        return url_for("home")
    return url_for("overview")


@contextmanager
def get_cursor():
    """Context manager wrapping db.get_cursor(): commits on success,
    rolls back on exception, and always closes the cursor.
    Usage:
        with get_cursor() as cursor:
            cursor.execute("SELECT ...")
    """
    cursor = db.get_cursor()
    try:
        yield cursor
        cursor.connection.commit()
    except Exception:
        cursor.connection.rollback()
        raise
    finally:
        cursor.close()
