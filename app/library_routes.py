# Library Routes
# Two sources, merged: the built-in reference documents that ship with the
# repo (app/static/library/manifest.json + PDFs in app/static/library/),
# and documents an admin uploads at runtime (tracked in Library_Documents,
# files stored in app/static/library_uploads/). The manifest side is
# read-only from the app's point of view - only the DB side can be added
# to or removed through the UI.

import json
import os
import re
import uuid
from functools import lru_cache

from flask import render_template, request, redirect, url_for, flash, session, abort, send_from_directory
from app import flask_app as app
import app.utils as utils
from app.repository import library_repository

LIBRARY_DIR = os.path.join(os.path.dirname(__file__), 'static', 'library')
MANIFEST_PATH = os.path.join(LIBRARY_DIR, 'manifest.json')
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'static', 'library_uploads')

MAX_PDF_BYTES = 20 * 1024 * 1024


@lru_cache(maxsize=1)
def _load_manifest():
    """Reads the built-in document list once and caches it - this file only
    changes when a developer adds a document to the repository, never at
    runtime, so the cache never needs invalidating."""
    try:
        with open(MANIFEST_PATH, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return []


def _uploaded_as_dict(row):
    """Shapes a Library_Documents row to look like a manifest entry, so the
    templates can treat both sources identically."""
    return {
        'slug': row['slug'],
        'title': row['title'],
        'description': row['description'] or '',
        'category': row['category'],
        'filename': row['filename'],
        'size_mb': float(row['size_mb']) if row['size_mb'] is not None else None,
        'is_uploaded': True,
        'document_id': row['document_id'],
    }


def _all_documents():
    manifest_docs = [{**d, 'is_uploaded': False} for d in _load_manifest()]
    uploaded_docs = [_uploaded_as_dict(r) for r in library_repository.list_all()]
    return manifest_docs + uploaded_docs


def _find_document(slug):
    manifest_hit = next((d for d in _load_manifest() if d['slug'] == slug), None)
    if manifest_hit:
        return {**manifest_hit, 'is_uploaded': False}
    row = library_repository.get_by_slug(slug)
    return _uploaded_as_dict(row) if row else None


def _slugify(title):
    """A short, URL-safe, unique-enough slug: the title's words plus 8
    random hex characters, so two documents with the same title never
    collide and nobody has to think of a unique name."""
    base = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:80] or 'document'
    return f"{base}-{uuid.uuid4().hex[:8]}"


def _save_pdf(file_storage):
    """Stores an uploaded PDF. Returns (filename, size_mb, error_message)."""
    if not file_storage or not file_storage.filename:
        return None, None, "Please choose a PDF file."

    if not file_storage.filename.lower().endswith('.pdf'):
        return None, None, "Only PDF files are accepted."

    data = file_storage.read()
    if not data:
        return None, None, "That file appears to be empty."
    if len(data) > MAX_PDF_BYTES:
        return None, None, "That PDF is larger than 20 MB."

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.pdf"
    with open(os.path.join(UPLOAD_DIR, filename), 'wb') as f:
        f.write(data)
    return filename, round(len(data) / (1024 * 1024), 2), None


@app.route("/library", methods=["GET"])
@utils.login_required()
def library():
    documents = _all_documents()
    query = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()

    if query:
        q = query.lower()
        documents = [
            d for d in documents
            if q in d['title'].lower()
            or q in (d.get('description') or '').lower()
            or q in d.get('category', '').lower()
        ]

    if category:
        documents = [d for d in documents if d.get('category') == category]

    categories = sorted({d.get('category', 'Other') for d in _all_documents()})

    return render_template(
        "library.html",
        documents=documents,
        categories=categories,
        query=query,
        active_category=category,
        total=len(_all_documents()),
    )


@app.route("/library/new", methods=["GET"])
@utils.login_required()
@utils.roles_required("Admin")
def new_library_document():
    return render_template("library_new.html", categories=library_repository.CATEGORIES)


@app.route("/library/new", methods=["POST"])
@utils.login_required()
@utils.roles_required("Admin")
def create_library_document():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    category = request.form.get("category", "").strip()

    def _redisplay(error_message):
        flash(error_message, "danger")
        return render_template(
            "library_new.html", categories=library_repository.CATEGORIES,
            form=request.form,
        )

    if not title:
        return _redisplay("A title is required.")
    if category not in library_repository.CATEGORIES:
        return _redisplay("Please choose one of the listed categories.")

    filename, size_mb, error = _save_pdf(request.files.get("pdf"))
    if error:
        return _redisplay(error)

    slug = _slugify(title)
    library_repository.create(
        slug, title, description or None, category, filename, size_mb, session["user_id"]
    )
    flash(f'"{title}" has been added to the library.', "success")
    return redirect(url_for("library_document", slug=slug))


@app.route("/library/<slug>", methods=["GET"])
@utils.login_required()
def library_document(slug):
    document = _find_document(slug)
    if not document:
        abort(404)
    return render_template("library_document.html", document=document)


@app.route("/library/<slug>/file", methods=["GET"])
@utils.login_required()
def library_file(slug):
    """Serves the PDF itself. Going through a route (rather than linking the
    static file directly) keeps the library behind the login check."""
    document = _find_document(slug)
    if not document:
        abort(404)
    directory = UPLOAD_DIR if document['is_uploaded'] else LIBRARY_DIR
    return send_from_directory(directory, document['filename'], mimetype='application/pdf')


@app.route("/library/<slug>/delete", methods=["POST"])
@utils.login_required()
@utils.roles_required("Admin")
def delete_library_document(slug):
    document = _find_document(slug)
    if not document:
        abort(404)

    if not document['is_uploaded']:
        flash("Built-in library documents can't be removed here.", "danger")
        return redirect(url_for("library_document", slug=slug))

    library_repository.delete(document['document_id'])
    try:
        os.remove(os.path.join(UPLOAD_DIR, document['filename']))
    except OSError:
        pass  # file already gone - the database record is what matters
    flash(f'"{document["title"]}" has been removed from the library.', "success")
    return redirect(url_for("library"))
