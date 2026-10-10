# Admin User Management Routes
# Everything an admin can do to an account after it's already been approved:
# deactivate/reactivate it, reassign a teacher's classroom, or trigger a
# password reset on the user's behalf. Approving/rejecting a brand-new
# sign-up request is handled separately in admin_routes.py.

import secrets
from datetime import datetime

from flask import render_template, request, redirect, url_for, flash, session
from app import flask_app as app
import app.utils as utils
from app.repository import user_repository, param_repository
from app.password_routes import _smtp_configured, _send_reset_email, TOKEN_LIFETIME


@app.route("/admin/users/<int:user_id>", methods=["GET"])
@utils.login_required()
@utils.roles_required("Admin")
def admin_user_detail(user_id):
    target = user_repository.get_user_by_id(user_id)
    if not target:
        flash("That account no longer exists.", "danger")
        return redirect(url_for("admin_dashboard"))

    return render_template(
        "admin_user_detail.html",
        target=target,
        classrooms=param_repository.get_classrooms(),
        is_self=(user_id == session["user_id"]),
    )


@app.route("/admin/users/<int:user_id>/suspend", methods=["POST"])
@utils.login_required()
@utils.roles_required("Admin")
def admin_suspend_user(user_id):
    if user_id == session["user_id"]:
        flash("You can't deactivate your own account.", "danger")
        return redirect(url_for("admin_user_detail", user_id=user_id))

    target = user_repository.get_user_by_id(user_id)
    if not target or target["status"] != "approved":
        flash("Only an approved account can be deactivated.", "danger")
        return redirect(url_for("admin_user_detail", user_id=user_id))

    user_repository.suspend_user(user_id)
    flash(f"{target['full_name']}'s account has been deactivated. "
          "Note: if they're currently signed in, they'll keep access until they log out.", "success")
    return redirect(url_for("admin_user_detail", user_id=user_id))


@app.route("/admin/users/<int:user_id>/reactivate", methods=["POST"])
@utils.login_required()
@utils.roles_required("Admin")
def admin_reactivate_user(user_id):
    target = user_repository.get_user_by_id(user_id)
    if not target or target["status"] != "suspended":
        flash("Only a deactivated account can be reactivated.", "danger")
        return redirect(url_for("admin_user_detail", user_id=user_id))

    user_repository.reactivate_user(user_id)
    flash(f"{target['full_name']}'s account has been reactivated.", "success")
    return redirect(url_for("admin_user_detail", user_id=user_id))


@app.route("/admin/users/<int:user_id>/classroom", methods=["POST"])
@utils.login_required()
@utils.roles_required("Admin")
def admin_update_classroom(user_id):
    target = user_repository.get_user_by_id(user_id)
    if not target or target["role"] != "Teacher":
        flash("Only a teacher's classroom can be reassigned.", "danger")
        return redirect(url_for("admin_user_detail", user_id=user_id))

    classroom = request.form.get("classroom", "").strip()
    if classroom not in param_repository.get_classrooms():
        flash("Please choose a valid classroom.", "danger")
        return redirect(url_for("admin_user_detail", user_id=user_id))

    user_repository.update_classroom(user_id, classroom)
    flash(f"{target['full_name']} has been reassigned to {classroom}.", "success")
    return redirect(url_for("admin_user_detail", user_id=user_id))


@app.route("/admin/users/<int:user_id>/reset-password", methods=["POST"])
@utils.login_required()
@utils.roles_required("Admin")
def admin_trigger_password_reset(user_id):
    """Same token/expiry mechanism as the self-service /forgot-password flow.
    If email is configured it's sent straight to the user; if not, the admin
    sees the link themselves to pass along - same no-SMTP fallback already
    used there, just reached from the admin side instead of the sign-in page."""
    target = user_repository.get_user_by_id(user_id)
    if not target or target["status"] not in ("approved", "suspended"):
        flash("Can't send a reset link for that account.", "danger")
        return redirect(url_for("admin_user_detail", user_id=user_id))

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + TOKEN_LIFETIME
    user_repository.set_reset_token(user_id, token, expires_at)
    reset_url = url_for("reset_password", token=token, _external=True)

    if _smtp_configured():
        try:
            _send_reset_email(target["email"], reset_url)
            flash(f"Reset link emailed to {target['email']}.", "success")
        except Exception as exc:
            app.logger.warning("Admin-triggered reset email failed: %s", exc)
            flash("Couldn't send the email right now. Try again shortly.", "danger")
        return redirect(url_for("admin_user_detail", user_id=user_id))

    # No SMTP configured - show the admin the link directly, same fallback
    # as the self-service flow, just visible to the admin instead of the user.
    return render_template(
        "admin_user_detail.html",
        target=target,
        classrooms=param_repository.get_classrooms(),
        is_self=(user_id == session["user_id"]),
        dev_reset_url=reset_url,
    )
