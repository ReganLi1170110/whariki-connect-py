# Admin Routes

from flask import render_template, request, redirect, url_for, flash
from app import flask_app as app
import app.utils as utils
from app.repository import admin_repository, user_repository, child_repository, notification_repository


@app.route("/admin", methods=["GET"])
@utils.login_required()
@utils.roles_required("Admin")
def admin_dashboard():
    stats = admin_repository.get_stats()
    users = admin_repository.list_all_users()
    pending_count = len(user_repository.list_pending_signups())
    return render_template("admin_dashboard.html", stats=stats, users=users, pending_count=pending_count)


@app.route("/admin/pending", methods=["GET"])
@utils.login_required()
@utils.roles_required("Admin")
def admin_pending_signups():
    return render_template(
        "admin_pending.html",
        pending=user_repository.list_pending_signups(),
        children=child_repository.list_all_children_basic(),
    )


@app.route("/admin/pending/<int:user_id>/approve", methods=["POST"])
@utils.login_required()
@utils.roles_required("Admin")
def admin_approve_signup(user_id):
    pending_user = user_repository.get_user_by_id(user_id)
    if not pending_user or pending_user["status"] != "pending":
        flash("That request is no longer pending.", "danger")
        return redirect(url_for("admin_pending_signups"))

    user_repository.approve_user(user_id)

    # If it's a parent, the admin can link them to their child/children
    # right here in the same step, since a new sign-up has no automatic
    # connection to any child yet.
    if pending_user["role"] == "Parent":
        child_ids = request.form.getlist("child_ids", type=int)
        child_repository.link_parent_to_children(user_id, child_ids)

    notification_repository.create(
        user_id, "message",
        "Your Whāriki Connect account has been approved — you can now sign in.",
    )

    flash(f"{pending_user['full_name']} has been approved.", "success")
    return redirect(url_for("admin_pending_signups"))


@app.route("/admin/pending/<int:user_id>/reject", methods=["POST"])
@utils.login_required()
@utils.roles_required("Admin")
def admin_reject_signup(user_id):
    pending_user = user_repository.get_user_by_id(user_id)
    if not pending_user or pending_user["status"] != "pending":
        flash("That request is no longer pending.", "danger")
        return redirect(url_for("admin_pending_signups"))

    user_repository.reject_user(user_id)
    flash(f"{pending_user['full_name']}'s request has been declined.", "success")
    return redirect(url_for("admin_pending_signups"))
