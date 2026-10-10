# Avatar Upload Helper
# Shared by app/profile_routes.py (self/child photo edits) and
# app/child_routes.py (admin creating a new child) so there's one place
# that decides what counts as a valid photo.

import os
import uuid

from werkzeug.utils import secure_filename

ALLOWED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
MAX_AVATAR_BYTES = 5 * 1024 * 1024
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'static', 'uploads')


def save_avatar(file_storage):
    """Stores an uploaded avatar. Returns (filename, error_message) - a
    filename of None with no error means nothing was uploaded, which is a
    valid choice (falls back to the initials avatar), not a failure."""
    if not file_storage or not file_storage.filename:
        return None, None

    extension = os.path.splitext(file_storage.filename)[1].lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        return None, "Photos must be PNG, JPG, GIF or WEBP."

    data = file_storage.read()
    if not data:
        return None, None
    if len(data) > MAX_AVATAR_BYTES:
        return None, "That photo is larger than 5 MB."

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    filename = secure_filename(f"{uuid.uuid4().hex}{extension}")
    with open(os.path.join(UPLOAD_DIR, filename), 'wb') as f:
        f.write(data)
    return filename, None
