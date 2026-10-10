# Message Routes

from flask import render_template, request, redirect, url_for, flash, session
from app import flask_app as app
import app.utils as utils
from app.repository import (
    message_repository,
    notification_repository,
    announcement_repository,
    param_repository,
)


def _current_user():
    return {
        "user_id": session["user_id"],
        "role": session["role"],
        "classroom": session.get("classroom"),
    }


@app.route("/messages", methods=["GET"])
@utils.login_required()
def messages():
    user = _current_user()
    contacts = message_repository.list_contacts_for_user(user)

    active_contact_id = request.args.get("with", type=int)
    active_child_id = request.args.get("child_id", type=int)
    thread = []

    if active_contact_id:
        # Mark before loading, so the thread you're currently reading
        # doesn't still show as unread.
        message_repository.mark_thread_read(session["user_id"], active_contact_id, active_child_id)
        thread = message_repository.list_thread(session["user_id"], active_contact_id, active_child_id)

    unread = message_repository.unread_counts_by_sender(session["user_id"])

    # Chat-history search. `q` is the search term; `scope=thread` limits it to
    # the conversation currently open, anything else searches every message.
    search_query = request.args.get("q", "").strip()
    search_scope = request.args.get("scope", "all")
    search_results = []
    if search_query:
        search_results = message_repository.search_messages(
            session["user_id"],
            search_query,
            other_user_id=active_contact_id if search_scope == "thread" else None,
            child_id=active_child_id if search_scope == "thread" else None,
        )

    # Broadcast/announcement composer target list: a teacher can only send
    # to their own room, so no picker is needed for them; an admin can
    # target any classroom, or the whole centre.
    announcement_classrooms = []
    if user["role"] == "Admin":
        announcement_classrooms = param_repository.get_classrooms() + [announcement_repository.ALL_CLASSROOMS_LABEL]

    return render_template(
        "messages.html",
        contacts=contacts,
        thread=thread,
        active_contact_id=active_contact_id,
        active_child_id=active_child_id,
        unread=unread,
        search_query=search_query,
        search_scope=search_scope,
        search_results=search_results,
        announcement_classrooms=announcement_classrooms,
    )


@app.route("/messages/announcement", methods=["POST"])
@utils.login_required()
@utils.roles_required("Teacher", "Admin")
def send_announcement():
    user = _current_user()
    content = request.form.get("content", "").strip()
    if not content:
        flash("Write a message before sending an announcement.", "danger")
        return redirect(url_for("messages"))

    if user["role"] == "Teacher":
        # A teacher can only broadcast to their own room - never trust a
        # hidden form field for this, always take it from the session.
        classroom = user["classroom"]
    else:
        classroom = request.form.get("classroom", "").strip()
        valid_classrooms = param_repository.get_classrooms() + [announcement_repository.ALL_CLASSROOMS_LABEL]
        if classroom not in valid_classrooms:
            flash("Please choose a valid classroom.", "danger")
            return redirect(url_for("messages"))

    recipient_ids = announcement_repository.recipients_for_classroom(classroom)
    if not recipient_ids:
        flash(f"No parents found for {classroom}.", "danger")
        return redirect(url_for("messages"))

    broadcast_id = announcement_repository.create_announcement(
        session["user_id"], classroom, content, len(recipient_ids)
    )
    for parent_id in recipient_ids:
        message_repository.send_broadcast_copy(session["user_id"], parent_id, content, broadcast_id)
        notification_repository.create(
            parent_id, "message", f"Announcement from {session['full_name']} ({classroom})."
        )

    flash(f"Announcement sent to {len(recipient_ids)} parent{'s' if len(recipient_ids) != 1 else ''}.", "success")
    return redirect(url_for("messages"))


@app.route("/messages/send", methods=["POST"])
@utils.login_required()
def send_message():
    receiver_id = request.form.get("receiver_id", type=int)
    child_id = request.form.get("child_id", type=int) or None
    content = request.form.get("content", "").strip()

    if not receiver_id or not content:
        flash("Message could not be sent.", "danger")
        return redirect(url_for("messages"))

    message_repository.send_message(session["user_id"], receiver_id, content, child_id)
    notification_repository.create(receiver_id, "message", f"New message from {session['full_name']}.")

    redirect_args = {"with": receiver_id}
    if child_id:
        redirect_args["child_id"] = child_id
    return redirect(url_for("messages", **redirect_args))
