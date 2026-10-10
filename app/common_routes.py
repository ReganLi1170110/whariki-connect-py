# Common Routes
# Handles the public landing/login pages and the shared "overview" dashboard.

from datetime import date

from flask import render_template, request, redirect, url_for, flash, session
from app import flask_app as app
import app.utils as utils
from app.repository import (
    user_repository, child_repository, notification_repository,
    attendance_repository, events_repository, accident_repository,
    learning_story_repository, timesheet_repository,
)


@app.route("/", methods=["GET"])
def home():
    if utils.is_logged_in():
        return redirect(url_for("overview"))
    return redirect(url_for("login"))


@app.route("/about", methods=["GET"])
def about():
    """Public marketing/help page - explains what the platform does and how
    to use it, split by role. Reachable without signing in."""
    return render_template("about.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if utils.is_logged_in():
        return redirect(url_for("overview"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user = user_repository.get_user_by_email(email)

        if not user or not utils.check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "danger")
            return render_template("login.html", email=email)

        if user["status"] == "pending":
            flash("Your account is still waiting for your centre admin to approve it. Please check back soon.", "danger")
            return render_template("login.html", email=email)

        if user["status"] == "rejected":
            flash("This sign-up request was not approved. Please contact your centre admin.", "danger")
            return render_template("login.html", email=email)

        if user["status"] == "suspended":
            flash("This account has been deactivated. Please contact your centre admin.", "danger")
            return render_template("login.html", email=email)

        session["user_id"] = user["user_id"]
        session["role"] = user["role"]
        session["full_name"] = user["full_name"]
        session["classroom"] = user["classroom"]

        flash(f"Welcome back, {user['full_name']}!", "success")
        return redirect(url_for("overview"))

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/overview", methods=["GET"])
@utils.login_required()
def overview():
    user = {
        "user_id": session["user_id"],
        "role": session["role"],
        "classroom": session.get("classroom"),
    }
    children = child_repository.list_children_for_user(user)
    notifications = notification_repository.list_for_user(session["user_id"], limit=5)
    unread_count = notification_repository.count_unread(session["user_id"])

    # Extra "what's happening" widgets for Parent/Teacher - Admin keeps the
    # plain summary since none of this is scoped to a single classroom for them.
    today_attendance = {}
    upcoming_events = []
    pending_accidents = []
    latest_story = None
    stories_this_week = 0
    timesheet_missing_days = 0

    if user["role"] in ("Parent", "Teacher"):
        child_ids = [c["child_id"] for c in children]
        today_attendance = attendance_repository.today_summary_for_children(child_ids)
        upcoming_events = events_repository.list_upcoming(user, limit=3)

        accidents = accident_repository.list_for_user(user)
        pending_accidents = [
            a for a in accidents
            if a["status"] == "submitted" and not a["parent_acknowledged_at"]
        ]

    if user["role"] == "Parent":
        stories = learning_story_repository.list_stories_for_user(user)
        latest_story = stories[0] if stories else None

    if user["role"] == "Teacher":
        stories = learning_story_repository.list_stories_for_user(user)
        week_start = timesheet_repository.week_start_for(date.today())
        stories_this_week = len([s for s in stories if s["created_at"].date() >= week_start])

        week_rows = timesheet_repository.list_week_for_teacher(session["user_id"], week_start)
        today = date.today()
        timesheet_missing_days = len([
            row for row in week_rows
            if row["date"].weekday() < 5 and row["date"] <= today and not row["entry"]
        ])

    return render_template(
        "overview.html",
        children=children,
        notifications=notifications,
        unread_count=unread_count,
        today_attendance=today_attendance,
        upcoming_events=upcoming_events,
        pending_accidents=pending_accidents,
        latest_story=latest_story,
        stories_this_week=stories_this_week,
        timesheet_missing_days=timesheet_missing_days,
        event_type_labels=events_repository.EVENT_TYPE_LABELS,
    )
