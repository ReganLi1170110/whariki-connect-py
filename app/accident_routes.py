# Accident / Incident Form Routes
# Accident forms have their own page. Only teachers can record one; parents
# can view and acknowledge submitted forms for their own children.

from datetime import datetime

from flask import render_template, request, redirect, url_for, flash, session, abort
from app import flask_app as app
import app.utils as utils
from app.repository import (
    child_repository, accident_repository,
    notification_repository, param_repository,
)


def _current_user():
    return {
        "user_id": session["user_id"],
        "role": session["role"],
        "classroom": session.get("classroom"),
    }


@app.route("/accidents", methods=["GET"])
@utils.login_required()
def accidents():
    user = _current_user()
    return render_template(
        "accidents.html",
        forms=accident_repository.list_for_user(user),
    )


@app.route("/accidents/new", methods=["GET"])
@utils.login_required()
@utils.roles_required("Teacher")
def new_accident():
    user = _current_user()
    return render_template(
        "accident_new.html",
        children=child_repository.list_children_for_user(user),
        injury_natures=param_repository.get_injury_natures(),
        body_parts=param_repository.get_accident_body_parts(),
        contact_methods=param_repository.get_contact_methods(),
        preselected_child_id=request.args.get("child_id", type=int),
        today=datetime.now().date().isoformat(),
    )


@app.route("/accidents/new", methods=["POST"])
@utils.login_required()
@utils.roles_required("Teacher")
def create_accident():
    user = _current_user()
    form = request.form

    child_id = form.get("child_id", type=int)
    incident_date_raw = form.get("incident_date", "")
    location = form.get("location", "").strip()
    description = form.get("description", "").strip()
    action_taken = form.get("action_taken", "").strip()
    # "Save draft" keeps it hidden from parents; "Submit" makes it visible.
    status = "draft" if form.get("action") == "draft" else "submitted"

    def _back_to_form(message):
        flash(message, "danger")
        return render_template(
            "accident_new.html",
            children=child_repository.list_children_for_user(user),
            injury_natures=param_repository.get_injury_natures(),
            body_parts=param_repository.get_accident_body_parts(),
            contact_methods=param_repository.get_contact_methods(),
            preselected_child_id=child_id,
            today=datetime.now().date().isoformat(),
            form=form,
        )

    if not child_id:
        return _back_to_form("Please choose which child this form is about.")
    if not child_repository.can_access_child(user, child_id):
        return _back_to_form("This child is not in your classroom.")
    if not incident_date_raw or not location or not description or not action_taken:
        return _back_to_form(
            "Date of incident, location, description and caregiver response are all required."
        )

    try:
        incident_date = datetime.strptime(incident_date_raw, "%Y-%m-%d").date()
    except ValueError:
        return _back_to_form("Invalid date of incident.")

    def _time_or_none(field):
        raw = form.get(field, "").strip()
        if not raw:
            return None
        try:
            return datetime.strptime(raw, "%H:%M").time()
        except ValueError:
            return None

    accident_id = accident_repository.create_accident_form({
        "child_id": child_id,
        "teacher_id": user["user_id"],
        "incident_date": incident_date,
        "incident_time": _time_or_none("incident_time"),
        "location": location,
        "nature_of_injury": form.get("nature_of_injury", "").strip() or None,
        "body_part": form.get("body_part", "").strip() or None,
        "description": description,
        "action_taken": action_taken,
        "additional_information": form.get("additional_information", "").strip() or None,
        "parent_contacted": form.get("parent_contacted") == "yes",
        "parent_contacted_name": form.get("parent_contacted_name", "").strip() or None,
        "contacted_by": form.get("contacted_by", "").strip() or None,
        "contact_method": form.get("contact_method", "").strip() or None,
        "contact_method_other": form.get("contact_method_other", "").strip() or None,
        "parent_contacted_time": _time_or_none("parent_contacted_time"),
        "other_actions_taken": form.get("other_actions_taken", "").strip() or None,
        "medical_attention_needed": form.get("medical_attention_needed") == "on",
        "notifiable_event": form.get("notifiable_event") == "on",
        "status": status,
        "provider_signature": form.get("provider_signature", "").strip() or None,
        "teacher_signed_at": datetime.now() if status == "submitted" else None,
    })

    if status == "submitted":
        notification_repository.create_for_parents_of_child(
            child_id, "accident_form",
            "A new accident/incident form has been filed for your child. "
            "Please review and acknowledge it.",
            accident_id,
        )
        flash("Accident form submitted and sent to the child's parents.", "success")
    else:
        flash("Draft saved. It stays hidden from parents until you submit it.", "success")

    return redirect(url_for("accidents"))


@app.route("/accidents/<int:accident_id>", methods=["GET"])
@utils.login_required()
def view_accident(accident_id):
    user = _current_user()
    form = accident_repository.get_accident(accident_id)
    if not form:
        abort(404)

    if not child_repository.can_access_child(user, form["child_id"]):
        flash("You do not have access to that form.", "danger")
        return redirect(url_for("accidents"))

    if user["role"] == "Parent" and form["status"] != "submitted":
        flash("That form hasn't been submitted yet.", "danger")
        return redirect(url_for("accidents"))

    return render_template("accident_view.html", form=form)


@app.route("/accidents/<int:accident_id>/acknowledge", methods=["POST"])
@utils.login_required()
@utils.roles_required("Parent")
def acknowledge_accident(accident_id):
    if accident_repository.acknowledge(accident_id, session["user_id"]):
        flash("Accident form acknowledged.", "success")
    else:
        flash("You can only acknowledge submitted forms for your own children.", "danger")
    return redirect(request.referrer or url_for("accidents"))
