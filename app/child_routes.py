# Child Routes
# The children list, and the single aggregated child-profile page that
# combines learning stories, attendance and accident forms in one place.

from datetime import date, datetime

from flask import render_template, redirect, url_for, flash, session, abort, request
from app import flask_app as app
import app.utils as utils
from app.avatar_utils import save_avatar
from app.repository import (
    routine_repository,
    child_repository,
    learning_story_repository,
    attendance_repository,
    accident_repository,
    param_repository,
    immunization_repository,
    pickup_repository,
    profile_repository,
)


def _current_user():
    return {
        "user_id": session["user_id"],
        "role": session["role"],
        "classroom": session.get("classroom"),
    }


@app.route("/children", methods=["GET"])
@utils.login_required()
def children_list():
    user = _current_user()
    # Only meaningful for Admin - Teacher/Parent never see withdrawn
    # children regardless of what's in the query string.
    show_withdrawn = user["role"] == "Admin" and request.args.get("show_withdrawn") == "1"
    children = child_repository.list_children_for_user(user, include_withdrawn=show_withdrawn)
    return render_template("children.html", children=children, show_withdrawn=show_withdrawn)


@app.route("/children/<int:child_id>", methods=["GET"])
@utils.login_required()
def child_profile(child_id):
    user = _current_user()

    if not child_repository.can_access_child(user, child_id):
        flash("You do not have access to that child's record.", "danger")
        return redirect(url_for("children_list"))

    child = child_repository.get_child_by_id(child_id)
    if not child:
        abort(404)

    # How many days of daily-routine history to pull back. Only a handful of
    # preset ranges are offered in the UI dropdown; anything else falls back
    # to the default so a hand-edited URL can't request an unbounded amount.
    ROUTINE_DAY_OPTIONS = (7, 15, 30)
    routine_days = request.args.get("routine_days", default=7, type=int)
    if routine_days not in ROUTINE_DAY_OPTIONS:
        routine_days = 7

    routines = routine_repository.list_for_child(child_id, limit_days=routine_days)
    routine_day_count = len({r["date"] for r in routines})

    return render_template(
        "child_profile.html",
        child=child,
        parents=child_repository.get_parents_for_child(child_id),
        stories=learning_story_repository.list_stories_for_child(child_id, user),
        attendance=attendance_repository.list_attendance_for_child(child_id),
        accidents=accident_repository.list_for_child(child_id, user),
        today_attendance=attendance_repository.get_attendance_for_date(child_id),
        today_iso=date.today().isoformat(),
        routines=routines,
        routine_days=routine_days,
        routine_day_options=ROUTINE_DAY_OPTIONS,
        routine_day_count=routine_day_count,
        meal_types=routine_repository.MEAL_TYPES,
        meal_outcomes=routine_repository.MEAL_OUTCOMES,
        toileting_types=routine_repository.TOILETING_TYPES,
        nappy_outcomes=routine_repository.NAPPY_OUTCOMES,
        toilet_outcomes=routine_repository.TOILET_OUTCOMES,
        immunizations=immunization_repository.list_for_child(child_id),
        pickups=pickup_repository.list_for_child(child_id),
        can_manage_pickups=(
            user["role"] == "Admin"
            or (user["role"] == "Parent" and profile_repository.parent_owns_child(user["user_id"], child_id))
        ),
        immunization_statuses=immunization_repository.STATUSES,
        vaccine_catalog=immunization_repository.VACCINE_CATALOG,
        dose_labels=immunization_repository.DOSE_LABELS,
        today_date=date.today(),
    )


@app.route("/children/<int:child_id>/health", methods=["POST"])
@utils.login_required()
def update_child_health(child_id):
    """Allergies, medical conditions, medications, dietary requirements and
    general medical notes. Editable by the child's own parent, or by any
    teacher/admin who can already see this child - the same access check
    used everywhere else on the profile page."""
    user = _current_user()
    if not child_repository.can_access_child(user, child_id):
        flash("You do not have access to that child's record.", "danger")
        return redirect(url_for("children_list"))

    child_repository.update_health_info(
        child_id,
        request.form.get("allergies", "").strip() or None,
        request.form.get("medical_conditions", "").strip() or None,
        request.form.get("medications", "").strip() or None,
        request.form.get("dietary_requirements", "").strip() or None,
        request.form.get("medical_notes", "").strip() or None,
    )
    flash("Health & safety information updated.", "success")
    return redirect(url_for("child_profile", child_id=child_id) + "#health")


@app.route("/children/new", methods=["GET"])
@utils.login_required()
@utils.roles_required("Admin")
def new_child():
    return render_template(
        "child_new.html",
        classrooms=param_repository.get_classrooms(),
        parents=child_repository.list_approved_parents(),
    )


@app.route("/children/new", methods=["POST"])
@utils.login_required()
@utils.roles_required("Admin")
def create_child():
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    dob_raw = request.form.get("date_of_birth", "").strip()
    classroom = request.form.get("classroom", "").strip()

    def _redisplay(error_message):
        flash(error_message, "danger")
        return render_template(
            "child_new.html",
            classrooms=param_repository.get_classrooms(),
            parents=child_repository.list_approved_parents(),
            form=request.form,
        )

    if not first_name or not last_name:
        return _redisplay("First and last name are both required.")

    try:
        date_of_birth = datetime.strptime(dob_raw, "%Y-%m-%d").date()
    except ValueError:
        return _redisplay("Please enter a valid date of birth.")

    if date_of_birth > date.today():
        return _redisplay("Date of birth can't be in the future.")

    valid_classrooms = param_repository.get_classrooms()
    if classroom not in valid_classrooms:
        return _redisplay("Please choose a valid classroom.")

    avatar_filename, avatar_error = save_avatar(request.files.get("avatar"))
    if avatar_error:
        return _redisplay(avatar_error)

    child_id = child_repository.create_child(
        first_name=first_name,
        last_name=last_name,
        date_of_birth=date_of_birth,
        classroom=classroom,
        emergency_contact=request.form.get("emergency_contact", "").strip() or None,
        emergency_phone=request.form.get("emergency_phone", "").strip() or None,
        allergies=request.form.get("allergies", "").strip() or None,
        medical_conditions=request.form.get("medical_conditions", "").strip() or None,
        medications=request.form.get("medications", "").strip() or None,
        dietary_requirements=request.form.get("dietary_requirements", "").strip() or None,
        medical_notes=request.form.get("medical_notes", "").strip() or None,
        avatar_url=avatar_filename,
    )

    parent_ids = request.form.getlist("parent_ids", type=int)
    if parent_ids:
        child_repository.link_parents_to_child(child_id, parent_ids)

    flash(f"{first_name} {last_name} has been added.", "success")
    return redirect(url_for("child_profile", child_id=child_id))


@app.route("/children/<int:child_id>/edit", methods=["GET"])
@utils.login_required()
@utils.roles_required("Admin")
def edit_child(child_id):
    child = child_repository.get_child_by_id(child_id)
    if not child:
        abort(404)
    return render_template(
        "child_edit.html", child=child, classrooms=param_repository.get_classrooms()
    )


@app.route("/children/<int:child_id>/edit", methods=["POST"])
@utils.login_required()
@utils.roles_required("Admin")
def update_child_basic_info(child_id):
    child = child_repository.get_child_by_id(child_id)
    if not child:
        abort(404)

    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    dob_raw = request.form.get("date_of_birth", "").strip()
    classroom = request.form.get("classroom", "").strip()

    def _redisplay(error_message):
        flash(error_message, "danger")
        return render_template(
            "child_edit.html", child=child, classrooms=param_repository.get_classrooms(),
            form=request.form,
        )

    if not first_name or not last_name:
        return _redisplay("First and last name are both required.")

    try:
        date_of_birth = datetime.strptime(dob_raw, "%Y-%m-%d").date()
    except ValueError:
        return _redisplay("Please enter a valid date of birth.")

    if date_of_birth > date.today():
        return _redisplay("Date of birth can't be in the future.")

    if classroom not in param_repository.get_classrooms():
        return _redisplay("Please choose a valid classroom.")

    child_repository.update_basic_info(child_id, first_name, last_name, date_of_birth, classroom)
    flash(f"{first_name} {last_name}'s details have been updated.", "success")
    return redirect(url_for("child_profile", child_id=child_id))


@app.route("/children/<int:child_id>/withdraw", methods=["POST"])
@utils.login_required()
@utils.roles_required("Admin")
def withdraw_child(child_id):
    child = child_repository.get_child_by_id(child_id)
    if not child:
        abort(404)

    raw_date = request.form.get("withdrawal_date", "").strip()
    try:
        withdrawal_date = datetime.strptime(raw_date, "%Y-%m-%d").date() if raw_date else date.today()
    except ValueError:
        withdrawal_date = date.today()

    child_repository.withdraw_child(
        child_id, withdrawal_date, request.form.get("withdrawal_notes", "").strip() or None
    )
    flash(f"{child['first_name']} {child['last_name']} has been marked as withdrawn. "
          "Their records are kept, just hidden from the default lists.", "success")
    return redirect(url_for("child_profile", child_id=child_id))


@app.route("/children/<int:child_id>/reenrol", methods=["POST"])
@utils.login_required()
@utils.roles_required("Admin")
def reenrol_child(child_id):
    child = child_repository.get_child_by_id(child_id)
    if not child:
        abort(404)

    child_repository.reenrol_child(child_id)
    flash(f"{child['first_name']} {child['last_name']} has been re-enrolled.", "success")
    return redirect(url_for("child_profile", child_id=child_id))
