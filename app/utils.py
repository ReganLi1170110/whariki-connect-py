from flask_bcrypt import Bcrypt
from flask import session, redirect, url_for, flash, request
from functools import wraps
from contextlib import contextmanager
from app import flask_app as app
from app.db import db

flask_bcrypt = Bcrypt(app)


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
