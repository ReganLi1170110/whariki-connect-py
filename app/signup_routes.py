# Signup Routes
# Public self-registration for parents and teachers. New accounts are
# created with status='pending' and must be approved by an admin (see
# admin_routes.py) before they can log in.

from flask import render_template, request, redirect, url_for, flash
from app import flask_app as app
import app.utils as utils
from app.repository import user_repository, centre_repository, notification_repository, param_repository


@app.route("/signup", methods=["GET"])
def signup():
    return render_template(
        "signup.html",
        centres=centre_repository.list_centres(),
        classrooms=param_repository.get_classrooms(),
    )


@app.route("/signup", methods=["POST"])
def signup_submit():
    role = request.form.get("role", "")
    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    centre_id = request.form.get("centre_id", type=int)
    classroom = request.form.get("classroom", "").strip() or None

    form_context = {
        "centres": centre_repository.list_centres(),
        "classrooms": param_repository.get_classrooms(),
        "full_name": full_name, "email": email, "role": role,
    }

    if role not in ("Parent", "Teacher"):
        flash("Please choose whether you're signing up as a parent or a teacher.", "danger")
        return render_template("signup.html", **form_context)

    if not full_name or not email or not password:
        flash("Name, email and password are all required.", "danger")
        return render_template("signup.html", **form_context)

    if len(password) < 8:
        flash("Password must be at least 8 characters.", "danger")
        return render_template("signup.html", **form_context)

    if not centre_id:
        flash("Please select your ECE centre.", "danger")
        return render_template("signup.html", **form_context)

    if role == "Teacher" and not classroom:
        flash("Please select which classroom/room you teach in.", "danger")
        return render_template("signup.html", **form_context)

    if user_repository.get_user_by_email(email):
        flash("An account with that email already exists. Try signing in instead.", "danger")
        return render_template("signup.html", **form_context)

    password_hash = utils.generate_password_hash(password)
    user_id = user_repository.create_pending_signup(
        role=role, full_name=full_name, email=email, password_hash=password_hash,
        centre_id=centre_id, classroom=classroom if role == "Teacher" else None,
    )

    # Notify every admin so they know a request is waiting for them.
    for admin_id in user_repository.list_admin_user_ids():
        notification_repository.create(
            admin_id, "message",
            f"New {role.lower()} sign-up request from {full_name} ({email}) is awaiting approval.",
            related_id=user_id,
        )

    flash("Thanks! Your request has been sent to your centre's admin. You'll be able to sign in once it's approved.", "success")
    return redirect(url_for("login"))
