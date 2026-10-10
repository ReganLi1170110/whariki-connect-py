# Routine Routes
# Daily care records (meals and toileting) for a child. Teachers record them;
# parents can view their own children's records only. Access is enforced by
# child_repository.can_access_child, the same check used elsewhere.

from datetime import datetime, date

from flask import request, redirect, url_for, flash, session
from app import flask_app as app
import app.utils as utils
from app.repository import child_repository, routine_repository


def _current_user():
    return {
        "user_id": session["user_id"],
        "role": session["role"],
        "classroom": session.get("classroom"),
    }


@app.route("/children/<int:child_id>/routines", methods=["POST"])
@utils.login_required()
@utils.roles_required("Teacher")
def create_routine(child_id):
    user = _current_user()
    if not child_repository.can_access_child(user, child_id):
        flash("This child is not in your classroom.", "danger")
        return redirect(url_for("children_list"))

    category = request.form.get("category", "")
    routine_type = request.form.get("routine_type", "").strip()
    outcome = request.form.get("outcome", "").strip() or None
    notes = request.form.get("notes", "").strip() or None
    raw_date = request.form.get("date", "")
    raw_time = request.form.get("time", "").strip()

    if category not in ("meal", "toileting"):
        flash("Please choose whether this is a meal or a toileting record.", "danger")
        return redirect(url_for("child_profile", child_id=child_id) + "#routines")

    valid_types = (routine_repository.MEAL_TYPES if category == "meal"
                   else routine_repository.TOILETING_TYPES)
    if routine_type not in valid_types:
        flash("Please choose a valid routine type.", "danger")
        return redirect(url_for("child_profile", child_id=child_id) + "#routines")

    try:
        on_date = datetime.strptime(raw_date, "%Y-%m-%d").date() if raw_date else date.today()
    except ValueError:
        flash("Invalid date.", "danger")
        return redirect(url_for("child_profile", child_id=child_id) + "#routines")

    try:
        at_time = datetime.strptime(raw_time, "%H:%M").time() if raw_time else datetime.now().time()
    except ValueError:
        at_time = datetime.now().time()

    routine_repository.create_routine(
        child_id=child_id,
        recorded_by=user["user_id"],
        on_date=on_date,
        category=category,
        routine_type=routine_type,
        outcome=outcome,
        recorded_at=datetime.combine(on_date, at_time),
        notes=notes,
    )

    flash(f"{routine_type} recorded.", "success")
    return redirect(url_for("child_profile", child_id=child_id) + "#routines")


@app.route("/children/<int:child_id>/routines/<int:routine_id>/delete", methods=["POST"])
@utils.login_required()
@utils.roles_required("Teacher")
def delete_routine(child_id, routine_id):
    user = _current_user()
    if not child_repository.can_access_child(user, child_id):
        flash("This child is not in your classroom.", "danger")
        return redirect(url_for("children_list"))

    routine_repository.delete_routine(routine_id, child_id)
    flash("Record removed.", "success")
    return redirect(url_for("child_profile", child_id=child_id) + "#routines")
