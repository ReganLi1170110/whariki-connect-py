# Profile Routes
# Every signed-in user maintains their own name, phone and photo. Parents can
# additionally maintain their own children's emergency contact and photo.

from flask import render_template, request, redirect, url_for, flash, session

from app import flask_app as app
import app.utils as utils
from app.avatar_utils import save_avatar as _save_avatar
from app.repository import profile_repository


@app.route("/profile", methods=["GET"])
@utils.login_required()
def profile():
    children = []
    if session.get("role") == "Parent":
        children = profile_repository.list_own_children(session["user_id"])
    return render_template(
        "profile.html",
        profile=profile_repository.get_profile(session["user_id"]),
        children=children,
    )


@app.route("/profile", methods=["POST"])
@utils.login_required()
def update_profile():
    full_name = request.form.get("full_name", "").strip()
    phone = request.form.get("phone", "").strip()

    if not full_name:
        flash("Your name can't be empty.", "danger")
        return redirect(url_for("profile"))

    avatar_filename, error = _save_avatar(request.files.get("avatar"))
    if error:
        flash(error, "danger")
        return redirect(url_for("profile"))

    profile_repository.update_own_details(session["user_id"], full_name, phone or None)
    if avatar_filename:
        profile_repository.update_own_avatar(session["user_id"], avatar_filename)

    # The sidebar reads the name from the session, so keep it in step.
    session["full_name"] = full_name
    flash("Your profile has been updated.", "success")
    return redirect(url_for("profile"))


@app.route("/profile/avatar/remove", methods=["POST"])
@utils.login_required()
def remove_profile_avatar():
    profile_repository.update_own_avatar(session["user_id"], None)
    flash("Photo removed — your initials will be shown instead.", "success")
    return redirect(url_for("profile"))


@app.route("/profile/child/<int:child_id>", methods=["POST"])
@utils.login_required()
@utils.roles_required("Parent")
def update_child_profile(child_id):
    if not profile_repository.parent_owns_child(session["user_id"], child_id):
        flash("You can only update your own children's details.", "danger")
        return redirect(url_for("profile"))

    avatar_filename, error = _save_avatar(request.files.get("avatar"))
    if error:
        flash(error, "danger")
        return redirect(url_for("profile"))

    profile_repository.update_child_emergency_contact(
        child_id,
        request.form.get("emergency_contact", "").strip() or None,
        request.form.get("emergency_phone", "").strip() or None,
    )
    profile_repository.update_child_health_info(
        child_id,
        request.form.get("allergies", "").strip() or None,
        request.form.get("medical_conditions", "").strip() or None,
        request.form.get("medications", "").strip() or None,
        request.form.get("dietary_requirements", "").strip() or None,
        request.form.get("medical_notes", "").strip() or None,
    )
    if avatar_filename:
        profile_repository.update_child_avatar(child_id, avatar_filename)

    flash("Your child's details have been updated.", "success")
    return redirect(url_for("profile"))


@app.route("/profile/child/<int:child_id>/avatar/remove", methods=["POST"])
@utils.login_required()
@utils.roles_required("Parent")
def remove_child_avatar(child_id):
    if not profile_repository.parent_owns_child(session["user_id"], child_id):
        flash("You can only update your own children's details.", "danger")
        return redirect(url_for("profile"))
    profile_repository.update_child_avatar(child_id, None)
    flash("Photo removed — your child's initials will be shown instead.", "success")
    return redirect(url_for("profile"))
