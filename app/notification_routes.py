# Notification Routes

from flask import render_template, redirect, url_for, session
from app import flask_app as app
import app.utils as utils
from app.repository import notification_repository


@app.route("/notifications", methods=["GET"])
@utils.login_required()
def notifications():
    items = notification_repository.list_for_user(session["user_id"])
    return render_template("notifications.html", notifications=items)


@app.route("/notifications/<int:notification_id>/read", methods=["POST"])
@utils.login_required()
def mark_notification_read(notification_id):
    notification_repository.mark_read(notification_id, session["user_id"])
    return redirect(url_for("notifications"))
