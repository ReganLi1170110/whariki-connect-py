# Immunization Routes
# NZ National Immunisation Schedule records. Teachers/admins record them
# (usually transcribed from a parent's Well Child book); parents view their
# own children's records only. Access is enforced by
# child_repository.can_access_child, the same check used elsewhere.

from datetime import datetime

from flask import request, redirect, url_for, flash, session
from app import flask_app as app
import app.utils as utils
from app.repository import child_repository, immunization_repository


def _current_user():
    return {
        "user_id": session["user_id"],
        "role": session["role"],
        "classroom": session.get("classroom"),
    }


@app.route("/children/<int:child_id>/immunizations", methods=["POST"])
@utils.login_required()
@utils.roles_required("Teacher", "Admin")
def create_immunization(child_id):
    user = _current_user()
    if not child_repository.can_access_child(user, child_id):
        flash("This child is not in your classroom.", "danger")
        return redirect(url_for("children_list"))

    vaccine_name = request.form.get("vaccine_name", "").strip()
    other_vaccine = request.form.get("vaccine_name_other", "").strip()
    if vaccine_name == "Other" and other_vaccine:
        vaccine_name = other_vaccine

    dose_label = request.form.get("dose_label", "").strip() or None
    status = request.form.get("status", "completed")
    notes = request.form.get("notes", "").strip() or None
    raw_date = request.form.get("date_given", "").strip()

    if not vaccine_name:
        flash("Please enter a vaccine name.", "danger")
        return redirect(url_for("child_profile", child_id=child_id) + "#immunizations")

    if status not in immunization_repository.STATUSES:
        status = "completed"

    date_given = None
    if raw_date:
        try:
            date_given = datetime.strptime(raw_date, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid date.", "danger")
            return redirect(url_for("child_profile", child_id=child_id) + "#immunizations")

    immunization_repository.create_immunization(
        child_id=child_id,
        recorded_by=user["user_id"],
        vaccine_name=vaccine_name,
        dose_label=dose_label,
        date_given=date_given,
        status=status,
        notes=notes,
    )

    flash(f"{vaccine_name} record added.", "success")
    return redirect(url_for("child_profile", child_id=child_id) + "#immunizations")


@app.route("/children/<int:child_id>/immunizations/<int:immunization_id>/delete", methods=["POST"])
@utils.login_required()
@utils.roles_required("Teacher", "Admin")
def delete_immunization(child_id, immunization_id):
    user = _current_user()
    if not child_repository.can_access_child(user, child_id):
        flash("This child is not in your classroom.", "danger")
        return redirect(url_for("children_list"))

    immunization_repository.delete_immunization(immunization_id, child_id)
    flash("Immunisation record removed.", "success")
    return redirect(url_for("child_profile", child_id=child_id) + "#immunizations")
