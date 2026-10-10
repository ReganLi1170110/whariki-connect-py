# Announcement Repository
# A teacher broadcasts one message to every parent in their classroom (or an
# admin broadcasts to one classroom or the whole centre). Each recipient
# gets their own row in Messages (so it shows up in their normal chat
# thread with the sender) tagged with the Announcements row it came from.

from app.utils import get_cursor

ALL_CLASSROOMS_LABEL = 'All classrooms'


def recipients_for_classroom(classroom):
    """Distinct parent user_ids to fan an announcement out to. A parent with
    two children in the same room is only counted - and messaged - once."""
    with get_cursor() as cursor:
        if classroom == ALL_CLASSROOMS_LABEL:
            cursor.execute(
                """SELECT DISTINCT pc.parent_id AS user_id
                   FROM Parent_Child pc JOIN Children c ON c.child_id = pc.child_id;"""
            )
        else:
            cursor.execute(
                """SELECT DISTINCT pc.parent_id AS user_id
                   FROM Parent_Child pc JOIN Children c ON c.child_id = pc.child_id
                   WHERE c.classroom = %s;""",
                (classroom,)
            )
        return [row['user_id'] for row in cursor.fetchall()]


def create_announcement(sender_id, classroom, content, recipient_count):
    with get_cursor() as cursor:
        cursor.execute(
            """INSERT INTO Announcements (sender_id, classroom, content, recipient_count)
               VALUES (%s, %s, %s, %s) RETURNING announcement_id;""",
            (sender_id, classroom, content, recipient_count)
        )
        return cursor.fetchone()['announcement_id']


def list_sent_by(sender_id, limit=20):
    """Recent announcements this teacher/admin has sent, for a short history
    list so they can see what already went out."""
    with get_cursor() as cursor:
        cursor.execute(
            """SELECT * FROM Announcements
               WHERE sender_id = %s
               ORDER BY created_at DESC LIMIT %s;""",
            (sender_id, limit)
        )
        return cursor.fetchall()
