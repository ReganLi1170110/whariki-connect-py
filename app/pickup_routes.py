# Authorized Pickup Routes
# Anyone who can view a child (Teacher/Admin/the child's own Parent) can see
# this list, since it's the whole point - staff need to check it at pickup
# time. Only the child's own parent or an admin can add/remove someone from
# it - a teacher sees the list but isn't the one maintaining it, the same
# split already used for emergency contact and health info.

from flask import request, redirect, url_for, flash, session
from app import flask_app as app
import app.utils as utils
from app.repository import child_repository, pickup_repository, profile_repository


def _current_user():
    return {
        "user_id": session["user_id"],
        "role": session["role"],
        "classroom": session.get("classroom"),
    }


def _can_manage(user, child_id):
    if user["role"] == "Admin":
        return True
    if user["role"] == "Parent":
        return profile_repository.parent_owns_child(user["user_id"], child_id)
    return False


@app.route("/children/<int:child_id>/pickups", methods=["POST"])
@utils.login_required()
def add_pickup_person(child_id):
    user = _current_user()
    if not _can_manage(user, child_id):
        flash("Only this child's own parent or an admin can update this list.", "danger")
        return redirect(url_for("child_profile", child_id=child_id) + "#pickups")

    full_name = request.form.get("full_name", "").strip()
    if not full_name:
        flash("A name is required.", "danger")
        return redirect(url_for("child_profile", child_id=child_id) + "#pickups")

    pickup_repository.add_pickup_person(
        child_id,
        full_name,
        request.form.get("phone", "").strip() or None,
        request.form.get("relationship", "").strip() or None,
        request.form.get("notes", "").strip() or None,
        user["user_id"],
    )
    flash(f"{full_name} added to the authorized pickup list.", "success")
    return redirect(url_for("child_profile", child_id=child_id) + "#pickups")


@app.route("/children/<int:child_id>/pickups/<int:pickup_id>/delete", methods=["POST"])
@utils.login_required()
def delete_pickup_person(child_id, pickup_id):
    user = _current_user()
    if not _can_manage(user, child_id):
        flash("Only this child's own parent or an admin can update this list.", "danger")
        return redirect(url_for("child_profile", child_id=child_id) + "#pickups")

    pickup_repository.delete_pickup_person(pickup_id, child_id)
    flash("Removed from the authorized pickup list.", "success")
    return redirect(url_for("child_profile", child_id=child_id) + "#pickups")
