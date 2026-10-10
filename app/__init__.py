# This script runs automatically when the `app` module is first loaded,
# and handles all the setup for the Flask app.
from flask import Flask, flash, request, session, redirect, url_for, g
from datetime import timedelta
from app.db import db
from app.db import connect

flask_app = Flask(__name__)
import os
# Read the session signing key from the environment (.env) when it is set,
# so a deployed copy never uses the key that is published in this repo. The
# fallback keeps local development working with no extra setup.
flask_app.secret_key = os.environ.get("SECRET_KEY") or 'whariki-connect-secret-key-comp693'
if not os.environ.get("SECRET_KEY"):
    flask_app.logger.warning("SECRET_KEY is not set - using the development key. Set it in .env before deploying.")
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


@flask_app.template_filter('striphtml')
def _striphtml(value, limit=None):
    """Plain-text preview of rich-text content, for list pages."""
    from app.sanitize import html_to_text
    return html_to_text(value, limit)


@flask_app.template_filter('first_image')
def _first_image(value):
    """URL of the first inline image in a story, used as the list thumbnail."""
    import re
    match = re.search(r'<img[^>]+src="([^"]+)"', value or '')
    return match.group(1) if match else None


@flask_app.template_filter('hours_worked')
def _hours_worked(entry):
    """Hours worked for one Timesheet_Entries row, for display in the grid."""
    from app.repository import timesheet_repository
    return timesheet_repository.hours_worked(entry)


@flask_app.context_processor
def inject_current_avatar():
    """The signed-in user's avatar, for the sidebar and top bar. Looked up per
    request so it updates immediately after an upload."""
    if not session.get("user_id"):
        return {"current_avatar": None}
    try:
        from app.repository import profile_repository
        row = profile_repository.get_profile(session["user_id"])
        return {"current_avatar": row["avatar_url"] if row else None}
    except Exception:
        # Never let a DB hiccup or missing column break page rendering.
        return {"current_avatar": None}


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
from app import password_routes
from app import signup_routes
from app import child_routes
from app import learning_story_routes
from app import attendance_routes
from app import message_routes
from app import accident_routes
from app import notification_routes
from app import admin_routes
from app import library_routes
from app import profile_routes
from app import routine_routes
from app import immunization_routes
from app import events_routes
from app import analytics_routes
from app import timesheet_routes
from app import admin_users_routes
from app import admin_params_routes
from app import pickup_routes
