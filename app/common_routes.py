# Common Routes
# Handles the public landing/login pages and the shared "overview" dashboard.

from flask import render_template, request, redirect, url_for, flash, session
from app import flask_app as app
import app.utils as utils
from app.repository import user_repository, child_repository, notification_repository


@app.route("/", methods=["GET"])
def home():
    if utils.is_logged_in():
        return redirect(url_for("overview"))
    return redirect(url_for("login"))


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

    return render_template(
        "overview.html",
        children=children,
        notifications=notifications,
        unread_count=unread_count,
    )
