# Events Repository
# Centre/classroom calendar: excursions, photo day, closed days, etc. Shown
# to everyone in scope ahead of time, rather than sent as a one-off message
# that scrolls out of an inbox.

from datetime import date as date_cls

from app.utils import get_cursor

ALL_CLASSROOMS_LABEL = 'All classrooms'  # matches the sentinel Announcements uses

EVENT_TYPES = ['excursion', 'photo_day', 'closed_day', 'other']
EVENT_TYPE_LABELS = {
    'excursion': 'Excursion',
    'photo_day': 'Photo day',
    'closed_day': 'Centre closed',
    'other': 'Other',
}


def _visibility_clause(user, alias='e'):
    """Parents see events for the whole centre plus their own children's
    room(s); teachers see the whole centre plus their own room; admins see
    everything. Mirrors the scoping already used for Announcements."""
    role = user['role']
    if role == 'Admin':
        return "", []
    if role == 'Teacher':
        return f" AND ({alias}.classroom = %s OR {alias}.classroom = %s)", \
               [user['classroom'], ALL_CLASSROOMS_LABEL]
    # Parent
    return f"""AND ({alias}.classroom = %s OR {alias}.classroom IN (
                    SELECT DISTINCT c.classroom FROM Children c
                    JOIN Parent_Child pc ON pc.child_id = c.child_id
                    WHERE pc.parent_id = %s
                ))""", [ALL_CLASSROOMS_LABEL, user['user_id']]


def list_upcoming(user, from_date=None, limit=100):
    from_date = from_date or date_cls.today()
    clause, extra_params = _visibility_clause(user)
    with get_cursor() as cursor:
        cursor.execute(
            f"""SELECT e.*, u.full_name AS created_by_name
                FROM Events e JOIN Users u ON u.user_id = e.created_by
                WHERE e.event_date >= %s {clause}
                ORDER BY e.event_date ASC, e.created_at ASC
                LIMIT %s;""",
            tuple([from_date] + extra_params + [limit])
        )
        return cursor.fetchall()


def list_past(user, before_date=None, limit=50):
    before_date = before_date or date_cls.today()
    clause, extra_params = _visibility_clause(user)
    with get_cursor() as cursor:
        cursor.execute(
            f"""SELECT e.*, u.full_name AS created_by_name
                FROM Events e JOIN Users u ON u.user_id = e.created_by
                WHERE e.event_date < %s {clause}
                ORDER BY e.event_date DESC, e.created_at DESC
                LIMIT %s;""",
            tuple([before_date] + extra_params + [limit])
        )
        return cursor.fetchall()


def get_event(event_id):
    with get_cursor() as cursor:
        cursor.execute(
            """SELECT e.*, u.full_name AS created_by_name
               FROM Events e JOIN Users u ON u.user_id = e.created_by
               WHERE e.event_id = %s;""",
            (event_id,)
        )
        return cursor.fetchone()


def user_can_see_event(user, event):
    """Server-side check mirroring _visibility_clause, for the single-event view."""
    role = user['role']
    if role == 'Admin':
        return True
    if event['classroom'] == ALL_CLASSROOMS_LABEL:
        return True
    if role == 'Teacher':
        return event['classroom'] == user['classroom']
    # Parent: does any of their children share this classroom?
    with get_cursor() as cursor:
        cursor.execute(
            """SELECT 1 FROM Children c
               JOIN Parent_Child pc ON pc.child_id = c.child_id
               WHERE pc.parent_id = %s AND c.classroom = %s LIMIT 1;""",
            (user['user_id'], event['classroom'])
        )
        return cursor.fetchone() is not None


def create_event(created_by, classroom, title, description, event_type, event_date, end_date=None):
    with get_cursor() as cursor:
        cursor.execute(
            """INSERT INTO Events
                 (created_by, classroom, title, description, event_type, event_date, end_date)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               RETURNING event_id;""",
            (created_by, classroom, title, description, event_type, event_date, end_date)
        )
        return cursor.fetchone()['event_id']


def delete_event(event_id, created_by=None):
    """created_by, when given, scopes the delete to the event's own author -
    used so a teacher can only remove events they created themselves."""
    with get_cursor() as cursor:
        if created_by:
            cursor.execute(
                "DELETE FROM Events WHERE event_id = %s AND created_by = %s;",
                (event_id, created_by)
            )
        else:
            cursor.execute("DELETE FROM Events WHERE event_id = %s;", (event_id,))


def recipients_for_classroom(classroom):
    """Reuses the same fan-out logic as Announcements: every parent whose
    child is in this classroom, or every parent centre-wide."""
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
