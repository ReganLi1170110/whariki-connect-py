# Message Routes

from flask import render_template, request, redirect, url_for, flash, session
from app import flask_app as app
import app.utils as utils
from app.repository import message_repository, notification_repository


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

    return render_template(
        "messages.html",
        contacts=contacts,
        thread=thread,
        active_contact_id=active_contact_id,
        active_child_id=active_child_id,
        unread=unread,
    )


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
