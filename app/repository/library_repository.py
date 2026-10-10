# Library Documents Repository
# Admin-uploaded reference PDFs, stored on top of the built-in set that
# ships with the repo (app/static/library/manifest.json - a separate,
# file-based source this repository never touches). The two are merged
# when the library page is rendered.

from app.utils import get_cursor

CATEGORIES = [
    'Compliance', 'Curriculum', 'Evaluation',
    'Legislation', 'Practice guidance', 'Professional practice',
]


def list_all():
    with get_cursor() as cursor:
        cursor.execute("SELECT * FROM Library_Documents ORDER BY created_at DESC;")
        return cursor.fetchall()


def get_by_slug(slug):
    with get_cursor() as cursor:
        cursor.execute("SELECT * FROM Library_Documents WHERE slug = %s;", (slug,))
        return cursor.fetchone()


def create(slug, title, description, category, filename, size_mb, uploaded_by):
    with get_cursor() as cursor:
        cursor.execute(
            """INSERT INTO Library_Documents
                 (slug, title, description, category, filename, size_mb, uploaded_by)
               VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING document_id;""",
            (slug, title, description, category, filename, size_mb, uploaded_by)
        )
        return cursor.fetchone()['document_id']


def delete(document_id):
    with get_cursor() as cursor:
        cursor.execute("DELETE FROM Library_Documents WHERE document_id = %s;", (document_id,))
