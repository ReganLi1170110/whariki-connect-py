# Child Routes
# The children list, and the single aggregated child-profile page that
# combines learning stories, attendance and accident forms in one place.

from flask import render_template, redirect, url_for, flash, session, abort
from app import flask_app as app
import app.utils as utils
from app.repository import (
    child_repository,
    learning_story_repository,
    attendance_repository,
    accident_repository,
    param_repository,
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
    children = child_repository.list_children_for_user(user)
    return render_template("children.html", children=children)


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

    return render_template(
        "child_profile.html",
        child=child,
        parents=child_repository.get_parents_for_child(child_id),
        stories=learning_story_repository.list_stories_for_child(child_id, user),
        attendance=attendance_repository.list_attendance_for_child(child_id),
        accidents=accident_repository.list_for_child(child_id, user),
        today_attendance=attendance_repository.get_attendance_for_date(child_id),
    )
