# Learning Story Routes
# Learning stories live on their own page (/learning-stories) rather than
# being buried inside the child profile.

import os
import uuid

from flask import render_template, request, redirect, url_for, flash, session, abort
from werkzeug.utils import secure_filename

from app import flask_app as app
import app.utils as utils
from app.repository import (
    child_repository, learning_story_repository,
    notification_repository, param_repository,
)

ALLOWED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'static', 'uploads')


def _current_user():
    return {
        "user_id": session["user_id"],
        "role": session["role"],
        "classroom": session.get("classroom"),
    }


def _save_uploaded_image(file_storage):
    """Saves an uploaded image and returns its stored filename, or None."""
    if not file_storage or not file_storage.filename:
        return None

    ext = os.path.splitext(file_storage.filename)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return None

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    # Randomise the stored name so two uploads called "photo.jpg" can coexist.
    filename = f"{uuid.uuid4().hex}{ext}"
    file_storage.save(os.path.join(UPLOAD_DIR, secure_filename(filename)))
    return filename


@app.route("/learning-stories", methods=["GET"])
@utils.login_required()
def learning_stories():
    user = _current_user()
    child_id = request.args.get("child_id", type=int)

    if child_id and not child_repository.can_access_child(user, child_id):
        flash("You do not have access to that child's records.", "danger")
        return redirect(url_for("learning_stories"))

    return render_template(
        "learning_stories.html",
        stories=learning_story_repository.list_stories_for_user(user, child_id),
        children=child_repository.list_children_for_user(user),
        active_child_id=child_id,
    )


@app.route("/learning-stories/new", methods=["GET"])
@utils.login_required()
@utils.roles_required("Teacher")
def new_learning_story():
    user = _current_user()
    return render_template(
        "learning_story_new.html",
        children=child_repository.list_children_for_user(user),
        strands=param_repository.get_curriculum_strands(),
        outcomes_by_strand=param_repository.get_learning_outcomes_by_strand(),
        preselected_child_id=request.args.get("child_id", type=int),
    )


@app.route("/learning-stories/new", methods=["POST"])
@utils.login_required()
@utils.roles_required("Teacher")
def create_learning_story():
    user = _current_user()

    child_id = request.form.get("child_id", type=int)
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    strands = request.form.getlist("strand")
    outcomes = request.form.getlist("outcome")
    # "Save draft" vs "Publish" - drafts stay hidden from parents.
    status = "draft" if request.form.get("action") == "draft" else "published"

    def _back_to_form(message):
        flash(message, "danger")
        return render_template(
            "learning_story_new.html",
            children=child_repository.list_children_for_user(user),
            strands=param_repository.get_curriculum_strands(),
            outcomes_by_strand=param_repository.get_learning_outcomes_by_strand(),
            preselected_child_id=child_id,
            title=title, content=content,
            selected_strands=strands, selected_outcomes=outcomes,
        )

    if not child_id:
        return _back_to_form("Please choose which child this story is about.")
    if not title or not content:
        return _back_to_form("Both a title and an observation are required.")
    if not child_repository.can_access_child(user, child_id):
        return _back_to_form("You can only write stories for children in your own classroom.")

    media_url = _save_uploaded_image(request.files.get("image"))
    if request.files.get("image") and request.files["image"].filename and not media_url:
        return _back_to_form("That image type isn't supported. Use PNG, JPG, GIF or WEBP.")

    story_id = learning_story_repository.create_story(
        child_id=child_id,
        teacher_id=user["user_id"],
        title=title,
        content=content,
        strands=strands,
        outcomes=outcomes,
        valid_strands=param_repository.get_curriculum_strands(),
        valid_outcomes=param_repository.get_all_learning_outcomes(),
        media_url=media_url,
        status=status,
    )

    if status == "published":
        notification_repository.create_for_parents_of_child(
            child_id, "learning_story",
            f'A new learning story "{title}" was posted.', story_id
        )
        flash("Learning story published.", "success")
    else:
        flash("Draft saved. It stays hidden from parents until you publish it.", "success")

    return redirect(url_for("learning_stories"))


@app.route("/learning-stories/<int:story_id>", methods=["GET"])
@utils.login_required()
def view_learning_story(story_id):
    user = _current_user()
    story = learning_story_repository.get_story(story_id)
    if not story:
        abort(404)

    if not child_repository.can_access_child(user, story["child_id"]):
        flash("You do not have access to that story.", "danger")
        return redirect(url_for("learning_stories"))

    # Parents must not see unpublished drafts.
    if user["role"] == "Parent" and story["status"] != "published":
        flash("That story hasn't been published yet.", "danger")
        return redirect(url_for("learning_stories"))

    return render_template("learning_story_view.html", story=story)
