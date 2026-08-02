# This script runs automatically when the `app` module is first loaded,
# and handles all the setup for the Flask app.
from flask import Flask, flash, request, session, redirect, url_for, g
from datetime import timedelta
from app.db import db
from app.db import connect

flask_app = Flask(__name__)
flask_app.secret_key = 'whariki-connect-secret-key-comp693'
flask_app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)

db.init_db(flask_app, connect.dbuser, connect.dbpass, connect.dbhost,
           connect.dbname, connect.dbport, connect.dbautocommit)


@flask_app.teardown_request
def handle_transaction(exception):
    conn = g.get("db", None)
    if not conn:
        return
    try:
        if exception:
            conn.rollback()
        else:
            conn.commit()
    except Exception:
        conn.rollback()


@flask_app.errorhandler(404)
def page_not_found(e):
    return redirect(url_for("home"))


@flask_app.errorhandler(500)
def handle_exception(e):
    flash("Something went wrong. Please try again.", "danger")
    return redirect(url_for("home"))


@flask_app.context_processor
def inject_sidebar_counts():
    """Makes the pending-signup and unread-message counts available to
    base.html on every page, so the sidebar links can show badges."""
    counts = {"sidebar_pending_count": 0, "sidebar_unread_messages": 0}
    if not session.get("user_id"):
        return counts

    from app.repository import message_repository
    counts["sidebar_unread_messages"] = message_repository.count_unread(session["user_id"])

    if session.get("role") == "Admin":
        from app.repository import user_repository
        counts["sidebar_pending_count"] = len(user_repository.list_pending_signups())

    return counts


# Import route modules so their @app.route decorators get registered.
from app import common_routes
from app import signup_routes
from app import child_routes
from app import learning_story_routes
from app import attendance_routes
from app import message_routes
from app import accident_routes
from app import notification_routes
from app import admin_routes
