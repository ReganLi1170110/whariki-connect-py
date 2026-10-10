# Attendance Repository

from datetime import date as date_cls
from app.utils import get_cursor


def list_attendance_for_child(child_id, limit=30):
    with get_cursor() as cursor:
        cursor.execute(
            """SELECT * FROM Attendance WHERE child_id = %s
               ORDER BY date DESC LIMIT %s;""",
            (child_id, limit)
        )
        return cursor.fetchall()


def list_attendance_for_month(child_id, year, month):
    """All attendance rows for one child in one calendar month, keyed by day
    number - used to render the teacher's month calendar."""
    with get_cursor() as cursor:
        cursor.execute(
            """SELECT * FROM Attendance
               WHERE child_id = %s
                 AND EXTRACT(YEAR FROM date) = %s
                 AND EXTRACT(MONTH FROM date) = %s
               ORDER BY date;""",
            (child_id, year, month)
        )
        return {row['date'].day: row for row in cursor.fetchall()}


def list_attendance_rows_for_month(child_id, year, month):
    """Same query as list_attendance_for_month but as an ordered list rather
    than a day-keyed dict - what the CSV/PDF export wants."""
    with get_cursor() as cursor:
        cursor.execute(
            """SELECT * FROM Attendance
               WHERE child_id = %s
                 AND EXTRACT(YEAR FROM date) = %s
                 AND EXTRACT(MONTH FROM date) = %s
               ORDER BY date;""",
            (child_id, year, month)
        )
        return cursor.fetchall()


def get_attendance_for_date(child_id, date=None):
    date = date or date_cls.today()
    with get_cursor() as cursor:
        cursor.execute(
            "SELECT * FROM Attendance WHERE child_id = %s AND date = %s;",
            (child_id, date)
        )
        return cursor.fetchone()


def check_in(child_id, recorded_by, date=None):
    date = date or date_cls.today()
    with get_cursor() as cursor:
        cursor.execute(
            """INSERT INTO Attendance (child_id, date, check_in_time, status, recorded_by)
               VALUES (%s, %s, now(), 'present', %s)
               ON CONFLICT (child_id, date)
               DO UPDATE SET check_in_time = now(), status = 'present', recorded_by = %s
               RETURNING *;""",
            (child_id, date, recorded_by, recorded_by)
        )
        return cursor.fetchone()


def check_out(child_id, date=None):
    date = date or date_cls.today()
    with get_cursor() as cursor:
        cursor.execute(
            """UPDATE Attendance SET check_out_time = now()
               WHERE child_id = %s AND date = %s RETURNING *;""",
            (child_id, date)
        )
        return cursor.fetchone()


def set_attendance(child_id, date, status, recorded_by,
                   check_in_time=None, check_out_time=None):
    """Teacher-only: overwrite a day's attendance from the calendar view,
    including back-dated corrections."""
    with get_cursor() as cursor:
        cursor.execute(
            """INSERT INTO Attendance
                 (child_id, date, status, recorded_by, check_in_time, check_out_time)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (child_id, date)
               DO UPDATE SET status = EXCLUDED.status,
                             recorded_by = EXCLUDED.recorded_by,
                             check_in_time = EXCLUDED.check_in_time,
                             check_out_time = EXCLUDED.check_out_time
               RETURNING *;""",
            (child_id, date, status, recorded_by, check_in_time, check_out_time)
        )
        return cursor.fetchone()


def today_summary_for_children(child_ids):
    """Today's row for a set of children, keyed by child_id - used by the
    attendance page so each child card can show its current state."""
    if not child_ids:
        return {}
    with get_cursor() as cursor:
        cursor.execute(
            "SELECT * FROM Attendance WHERE date = CURRENT_DATE AND child_id = ANY(%s);",
            (list(child_ids),)
        )
        return {row['child_id']: row for row in cursor.fetchall()}


def list_history_for_children(child_ids, start_date=None, end_date=None, status=None, limit=300):
    """Attendance records across every child a user can access, newest
    first, optionally narrowed by date range and/or status - what the
    Attendance history/search page filters against. Without this, the only
    way to look something up was one child's month calendar at a time."""
    if not child_ids:
        return []
    sql = """SELECT a.*, c.first_name, c.last_name, c.classroom
             FROM Attendance a JOIN Children c ON c.child_id = a.child_id
             WHERE a.child_id = ANY(%s)"""
    params = [list(child_ids)]

    if start_date:
        sql += " AND a.date >= %s"
        params.append(start_date)
    if end_date:
        sql += " AND a.date <= %s"
        params.append(end_date)
    if status:
        sql += " AND a.status = %s"
        params.append(status)

    sql += " ORDER BY a.date DESC, c.first_name LIMIT %s;"
    params.append(limit)

    with get_cursor() as cursor:
        cursor.execute(sql, tuple(params))
        return cursor.fetchall()
