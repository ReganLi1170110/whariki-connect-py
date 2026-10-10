# Events Routes
# Centre/classroom calendar. Teachers and admins create events; everyone in
# scope can view them, mirroring how Announcements are scoped.

from datetime import datetime

from flask import render_template, request, redirect, url_for, flash, session, abort
from app import flask_app as app
import app.utils as utils
from app.repository import events_repository, notification_repository, param_repository


def _current_user():
    return {
        "user_id": session["user_id"],
        "role": session["role"],
        "classroom": session.get("classroom"),
    }


@app.route("/events", methods=["GET"])
@utils.login_required()
def events():
    user = _current_user()
    return render_template(
        "events.html",
        upcoming=events_repository.list_upcoming(user),
        past=events_repository.list_past(user),
        event_type_labels=events_repository.EVENT_TYPE_LABELS,
    )


@app.route("/events/new", methods=["GET"])
@utils.login_required()
@utils.roles_required("Teacher", "Admin")
def new_event():
    user = _current_user()
    classrooms = param_repository.get_classrooms()
    return render_template(
        "event_new.html",
        classrooms=classrooms if user["role"] == "Admin" else None,
        own_classroom=user["classroom"],
        event_types=events_repository.EVENT_TYPES,
        event_type_labels=events_repository.EVENT_TYPE_LABELS,
    )


@app.route("/events/new", methods=["POST"])
@utils.login_required()
@utils.roles_required("Teacher", "Admin")
def create_event():
    user = _current_user()
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip() or None
    event_type = request.form.get("event_type", "other")
    audience = request.form.get("audience", "classroom")
    raw_date = request.form.get("event_date", "")
    raw_end_date = request.form.get("end_date", "").strip()

    def _back_to_form(message):
        flash(message, "danger")
        classrooms = param_repository.get_classrooms()
        return render_template(
            "event_new.html",
            classrooms=classrooms if user["role"] == "Admin" else None,
            own_classroom=user["classroom"],
            event_types=events_repository.EVENT_TYPES,
            event_type_labels=events_repository.EVENT_TYPE_LABELS,
            title=title, description=description, event_type=event_type,
            audience=audience, event_date=raw_date, end_date=raw_end_date,
        )

    if not title:
        return _back_to_form("A title is required.")

    if event_type not in events_repository.EVENT_TYPES:
        event_type = "other"

    try:
        event_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
    except ValueError:
        return _back_to_form("Please choose a valid date.")

    end_date = None
    if raw_end_date:
        try:
            end_date = datetime.strptime(raw_end_date, "%Y-%m-%d").date()
        except ValueError:
            return _back_to_form("Please choose a valid end date.")
        if end_date < event_date:
            return _back_to_form("The end date can't be before the start date.")

    # A teacher can only post to their own room or the whole centre - never
    # trust a classroom value sent from the browser for anything else.
    if user["role"] == "Teacher":
        classroom = (events_repository.ALL_CLASSROOMS_LABEL if audience == "centre"
                    else user["classroom"])
    elif audience == "centre":
        classroom = events_repository.ALL_CLASSROOMS_LABEL
    else:
        valid_classrooms = param_repository.get_classrooms()
        classroom = request.form.get("classroom", "").strip()
        if classroom not in valid_classrooms:
            return _back_to_form("Please choose a valid classroom.")

    event_id = events_repository.create_event(
        created_by=user["user_id"], classroom=classroom, title=title,
        description=description, event_type=event_type,
        event_date=event_date, end_date=end_date,
    )

    for parent_id in events_repository.recipients_for_classroom(classroom):
        notification_repository.create(
            parent_id, "event",
            f'New event: "{title}" on {event_date.strftime("%d %b %Y")}.',
            event_id,
        )

    flash("Event added to the calendar.", "success")
    return redirect(url_for("events"))


@app.route("/events/<int:event_id>", methods=["GET"])
@utils.login_required()
def view_event(event_id):
    user = _current_user()
    event = events_repository.get_event(event_id)
    if not event:
        abort(404)

    if not events_repository.user_can_see_event(user, event):
        flash("You do not have access to that event.", "danger")
        return redirect(url_for("events"))

    can_delete = user["role"] == "Admin" or (
        user["role"] == "Teacher" and event["created_by"] == user["user_id"]
    )

    return render_template(
        "event_view.html", event=event,
        event_type_labels=events_repository.EVENT_TYPE_LABELS, can_delete=can_delete,
    )


@app.route("/events/<int:event_id>/delete", methods=["POST"])
@utils.login_required()
@utils.roles_required("Teacher", "Admin")
def delete_event(event_id):
    user = _current_user()
    event = events_repository.get_event(event_id)
    if not event:
        abort(404)

    if user["role"] == "Admin":
        events_repository.delete_event(event_id)
    elif event["created_by"] == user["user_id"]:
        events_repository.delete_event(event_id, created_by=user["user_id"])
    else:
        flash("You can only remove events you created yourself.", "danger")
        return redirect(url_for("view_event", event_id=event_id))

    flash("Event removed.", "success")
    return redirect(url_for("events"))
