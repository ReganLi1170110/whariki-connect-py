# Routine Repository
# Daily care records: meals (morning tea, lunch, afternoon tea) and toileting
# (nappy changes, independent toilet use).

from datetime import date as date_cls

from app.utils import get_cursor

MEAL_TYPES = ['Morning tea', 'Lunch', 'Afternoon tea']
MEAL_OUTCOMES = ['All', 'Most', 'Some', 'None']
TOILETING_TYPES = ['Nappy change', 'Toilet']
NAPPY_OUTCOMES = ['Wet', 'Soiled', 'Dry']
TOILET_OUTCOMES = ['Success', 'Accident']


def list_for_child(child_id, limit_days=30):
    """All routine records for a child, newest day first, grouped by date in
    the caller. limit_days caps how many distinct days come back."""
    with get_cursor() as cursor:
        cursor.execute(
            """SELECT r.*, u.full_name AS recorded_by_name
               FROM Routines r
               LEFT JOIN Users u ON u.user_id = r.recorded_by
               WHERE r.child_id = %s
                 AND r.date IN (
                     SELECT DISTINCT date FROM Routines
                     WHERE child_id = %s ORDER BY date DESC LIMIT %s
                 )
               ORDER BY r.date DESC, r.recorded_at ASC;""",
            (child_id, child_id, limit_days)
        )
        return cursor.fetchall()


def list_for_child_on_date(child_id, on_date):
    with get_cursor() as cursor:
        cursor.execute(
            """SELECT r.*, u.full_name AS recorded_by_name
               FROM Routines r
               LEFT JOIN Users u ON u.user_id = r.recorded_by
               WHERE r.child_id = %s AND r.date = %s
               ORDER BY r.recorded_at ASC;""",
            (child_id, on_date)
        )
        return cursor.fetchall()


def create_routine(child_id, recorded_by, on_date, category, routine_type,
                   outcome, recorded_at, notes=None):
    with get_cursor() as cursor:
        cursor.execute(
            """INSERT INTO Routines
                 (child_id, recorded_by, date, category, routine_type,
                  outcome, recorded_at, notes)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
               RETURNING routine_id;""",
            (child_id, recorded_by, on_date, category, routine_type,
             outcome, recorded_at, notes)
        )
        return cursor.fetchone()['routine_id']


def delete_routine(routine_id, child_id):
    """Scoped by child_id so a teacher can't delete a record by guessing an id."""
    with get_cursor() as cursor:
        cursor.execute(
            "DELETE FROM Routines WHERE routine_id = %s AND child_id = %s;",
            (routine_id, child_id)
        )


def summary_for_today(child_ids):
    """Counts of today's meal and toileting records per child."""
    if not child_ids:
        return {}
    with get_cursor() as cursor:
        cursor.execute(
            """SELECT child_id,
                      COUNT(*) FILTER (WHERE category = 'meal')::int AS meals,
                      COUNT(*) FILTER (WHERE category = 'toileting')::int AS toileting
               FROM Routines
               WHERE date = CURRENT_DATE AND child_id = ANY(%s)
               GROUP BY child_id;""",
            (list(child_ids),)
        )
        return {row['child_id']: row for row in cursor.fetchall()}
