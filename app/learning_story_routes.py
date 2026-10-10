# Learning Story Routes
# Learning stories live on their own page (/learning-stories) rather than
# being buried inside the child profile. The observation field is a rich-text
# editor, so its content arrives as HTML and is sanitised before storage.

import base64
import binascii
import json
import os
import uuid
from datetime import datetime

from flask import render_template, request, redirect, url_for, flash, session, abort, jsonify
from werkzeug.utils import secure_filename

from app import flask_app as app
import app.utils as utils
from app import ai_assistant
from app.sanitize import clean_html, html_to_text
from app.repository import (
    child_repository, learning_story_repository,
    notification_repository, param_repository,
)

ALLOWED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
MAX_IMAGE_BYTES = 6 * 1024 * 1024  # 6 MB per pasted/uploaded image

# Maps the browser's mime type to the extension we store the file under.
MIME_EXTENSIONS = {
    'image/png': '.png', 'image/jpeg': '.jpg', 'image/jpg': '.jpg',
    'image/gif': '.gif', 'image/webp': '.webp',
}


def _current_user():
    return {
        "user_id": session["user_id"],
        "role": session["role"],
        "classroom": session.get("classroom"),
    }


def _store_image_bytes(data, extension):
    """Writes image bytes to the uploads folder and returns the public URL."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    filename = secure_filename(f"{uuid.uuid4().hex}{extension}")
    with open(os.path.join(UPLOAD_DIR, filename), 'wb') as f:
        f.write(data)
    return f"/static/uploads/{filename}"


@app.route("/learning-stories", methods=["GET"])
@utils.login_required()
def learning_stories():
    user = _current_user()
    child_id = request.args.get("child_id", type=int)
    strand = request.args.get("strand", "").strip() or None

    def _parse_date(name):
        raw = request.args.get(name, "").strip()
        if not raw:
            return None
        try:
            return datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            return None

    start_date = _parse_date("start_date")
    end_date = _parse_date("end_date")

    if child_id and not child_repository.can_access_child(user, child_id):
        flash("You do not have access to that child's records.", "danger")
        return redirect(url_for("learning_stories"))

    return render_template(
        "learning_stories.html",
        stories=learning_story_repository.list_stories_for_user(
            user, child_id, start_date, end_date, strand
        ),
        children=child_repository.list_children_for_user(user),
        strands=param_repository.get_curriculum_strands(),
        active_child_id=child_id,
        active_strand=strand,
        active_start_date=request.args.get("start_date", ""),
        active_end_date=request.args.get("end_date", ""),
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


@app.route("/learning-stories/upload-image", methods=["POST"])
@utils.login_required()
@utils.roles_required("Teacher")
def upload_story_image():
    """Called by the editor when a teacher pastes, drops or picks an image.
    Returns the stored URL so the editor can insert it inline."""
    file_storage = request.files.get("image")
    if file_storage and file_storage.filename:
        extension = os.path.splitext(file_storage.filename)[1].lower()
        if extension not in ALLOWED_IMAGE_EXTENSIONS:
            return jsonify(error="Unsupported image type. Use PNG, JPG, GIF or WEBP."), 400
        data = file_storage.read()
        if len(data) > MAX_IMAGE_BYTES:
            return jsonify(error="That image is larger than 6 MB."), 400
        return jsonify(url=_store_image_bytes(data, extension))

    # Pasted images arrive as a base64 data URL rather than a file upload.
    data_url = (request.json or {}).get("data_url") if request.is_json else None
    if data_url and data_url.startswith("data:"):
        header, _, encoded = data_url.partition(',')
        mime = header[5:].split(';')[0].lower()
        extension = MIME_EXTENSIONS.get(mime)
        if not extension:
            return jsonify(error="Unsupported image type."), 400
        try:
            data = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError):
            return jsonify(error="That image could not be read."), 400
        if len(data) > MAX_IMAGE_BYTES:
            return jsonify(error="That image is larger than 6 MB."), 400
        return jsonify(url=_store_image_bytes(data, extension))

    return jsonify(error="No image was received."), 400


@app.route("/learning-stories/ai-assist", methods=["POST"])
@utils.login_required()
@utils.roles_required("Teacher")
def learning_story_ai_assist():
    """Back-and-forth AI helper for drafting a learning story.

    The provider (Groq by default, Gemini optional) lives in app/ai_assistant.py
    so swapping it doesn't touch this route.
    """
    payload = request.get_json(silent=True) or {}
    history = payload.get("history") or []
    # Privacy (UAT feedback): only the child's first name ever leaves the
    # app. The editor already sends just the first name; keeping only the
    # first word here means a surname can't slip through either.
    child_name = ((payload.get("child_name") or "").strip().split() or ["the child"])[0]
    draft = html_to_text(payload.get("draft") or "", limit=1500)

    if not history:
        return jsonify(error="No question was provided."), 400

    try:
        reply = ai_assistant.ask(child_name, draft, history)
    except ai_assistant.AINotConfigured as exc:
        # Not an error - the feature is simply switched off.
        return jsonify(reply=exc.message, configured=False)
    except ai_assistant.AIError as exc:
        app.logger.warning("AI assistant error: %s", exc.message)
        return jsonify(error=exc.message), exc.status

    return jsonify(reply=reply, configured=True)


@app.route("/ai-status", methods=["GET"])
@utils.login_required()
@utils.roles_required("Teacher", "Admin")
def ai_status():
    """Self-check page: confirms the key is loaded and makes one live test call,
    so configuration problems surface here rather than mid-way through writing."""
    info = ai_assistant.status()
    test_result = None

    if request.args.get("test") and info["key_present"]:
        try:
            reply = ai_assistant.ask(
                "Tama", "",
                [{"role": "user", "content": "Reply with exactly: AI assistant is working."}],
            )
            test_result = {"ok": True, "message": reply.strip()}
        except ai_assistant.AINotConfigured as exc:
            test_result = {"ok": False, "message": exc.message}
        except ai_assistant.AIError as exc:
            test_result = {"ok": False, "message": exc.message}

    return render_template("ai_status.html", info=info, test_result=test_result)


@app.route("/learning-stories/new", methods=["POST"])
@utils.login_required()
@utils.roles_required("Teacher")
def create_learning_story():
    user = _current_user()

    child_id = request.form.get("child_id", type=int)
    title = request.form.get("title", "").strip()
    content_html = clean_html(request.form.get("content", ""))
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
            title=title, content=content_html,
            selected_strands=strands, selected_outcomes=outcomes,
        )

    if not child_id:
        return _back_to_form("Please choose which child this story is about.")
    if not title:
        return _back_to_form("A title is required.")
    # An "empty" editor still submits markup like <p><br></p>, so check the text.
    if not html_to_text(content_html) and '<img' not in content_html:
        return _back_to_form("Please write an observation.")
    if not child_repository.can_access_child(user, child_id):
        return _back_to_form("You can only write stories for children in your own classroom.")

    story_id = learning_story_repository.create_story(
        child_id=child_id,
        teacher_id=user["user_id"],
        title=title,
        content=content_html,
        strands=strands,
        outcomes=outcomes,
        valid_strands=param_repository.get_curriculum_strands(),
        valid_outcomes=param_repository.get_all_learning_outcomes(),
        media_url=None,
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
