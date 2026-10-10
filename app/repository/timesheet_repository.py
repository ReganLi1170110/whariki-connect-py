# Timesheet Repository
# Actual hours worked, as opposed to Attendance (which is about children) or
# any future rostering feature (which would be planned rather than actual
# hours). A teacher fills in and edits their own entries; once an admin
# approves an entry it is locked for the teacher, though an admin can always
# change it.

from datetime import datetime, timedelta

from app.utils import get_cursor


def week_start_for(any_date):
    """Monday of the week containing any_date."""
    return any_date - timedelta(days=any_date.weekday())


def hours_worked(entry):
    """(end_time - start_time) - break, in hours, rounded to 2dp. Handles the
    ordinary case only - end_time is always assumed to be after start_time on
    the same day, which matches how the entry form collects it."""
    start = datetime.combine(entry['work_date'], entry['start_time'])
    end = datetime.combine(entry['work_date'], entry['end_time'])
    minutes = (end - start).total_seconds() / 60 - entry['break_minutes']
    return round(max(minutes, 0) / 60, 2)


def list_week_for_teacher(teacher_id, week_start):
    """Always returns exactly 7 rows (Mon-Sun), with entry=None for days that
    have nothing recorded yet, so the weekly grid template never has to
    special-case a missing day."""
    week_end = week_start + timedelta(days=6)
    with get_cursor() as cursor:
        cursor.execute(
            """SELECT * FROM Timesheet_Entries
               WHERE teacher_id = %s AND work_date BETWEEN %s AND %s;""",
            (teacher_id, week_start, week_end)
        )
        by_date = {row['work_date']: row for row in cursor.fetchall()}

    return [
        {'date': week_start + timedelta(days=i), 'entry': by_date.get(week_start + timedelta(days=i))}
        for i in range(7)
    ]


def get_entry(teacher_id, work_date):
    with get_cursor() as cursor:
        cursor.execute(
            "SELECT * FROM Timesheet_Entries WHERE teacher_id = %s AND work_date = %s;",
            (teacher_id, work_date)
        )
        return cursor.fetchone()


def upsert_entry(teacher_id, work_date, start_time, end_time, break_minutes, notes, edited_by):
    """Insert or update one day's entry. Does not check status='approved' -
    that check belongs in the route, where it can be reported back to the
    user rather than silently doing nothing."""
    with get_cursor() as cursor:
        cursor.execute(
            """INSERT INTO Timesheet_Entries
                 (teacher_id, work_date, start_time, end_time, break_minutes,
                  notes, last_edited_by, updated_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, now())
               ON CONFLICT (teacher_id, work_date) DO UPDATE SET
                 start_time = EXCLUDED.start_time,
                 end_time = EXCLUDED.end_time,
                 break_minutes = EXCLUDED.break_minutes,
                 notes = EXCLUDED.notes,
                 last_edited_by = EXCLUDED.last_edited_by,
                 updated_at = now();""",
            (teacher_id, work_date, start_time, end_time, break_minutes, notes, edited_by)
        )


def delete_entry(teacher_id, work_date):
    with get_cursor() as cursor:
        cursor.execute(
            "DELETE FROM Timesheet_Entries WHERE teacher_id = %s AND work_date = %s;",
            (teacher_id, work_date)
        )


def approve_week(teacher_id, week_start, approved_by):
    week_end = week_start + timedelta(days=6)
    with get_cursor() as cursor:
        cursor.execute(
            """UPDATE Timesheet_Entries SET status = 'approved', last_edited_by = %s, updated_at = now()
               WHERE teacher_id = %s AND work_date BETWEEN %s AND %s;""",
            (approved_by, teacher_id, week_start, week_end)
        )


def unapprove_week(teacher_id, week_start, edited_by):
    week_end = week_start + timedelta(days=6)
    with get_cursor() as cursor:
        cursor.execute(
            """UPDATE Timesheet_Entries SET status = 'submitted', last_edited_by = %s, updated_at = now()
               WHERE teacher_id = %s AND work_date BETWEEN %s AND %s;""",
            (edited_by, teacher_id, week_start, week_end)
        )


def list_teachers():
    """For the admin's teacher picker."""
    with get_cursor() as cursor:
        cursor.execute(
            "SELECT user_id, full_name, classroom FROM Users "
            "WHERE role = 'Teacher' AND status = 'approved' ORDER BY full_name;"
        )
        return cursor.fetchall()


def monthly_totals_for_all_teachers(year, month):
    """One row per teacher with their total hours for the month - the
    at-a-glance table on the admin overview page. Computed in Python via
    list_week_for_teacher-style per-row math would mean N+1 queries, so this
    pulls the raw rows in one query and sums them here instead."""
    with get_cursor() as cursor:
        cursor.execute(
            """SELECT te.*, u.full_name AS teacher_name
               FROM Timesheet_Entries te JOIN Users u ON u.user_id = te.teacher_id
               WHERE EXTRACT(YEAR FROM te.work_date) = %s
                 AND EXTRACT(MONTH FROM te.work_date) = %s;""",
            (year, month)
        )
        rows = cursor.fetchall()

    totals = {}
    for row in rows:
        key = row['teacher_id']
        if key not in totals:
            totals[key] = {'teacher_name': row['teacher_name'], 'hours': 0.0, 'days': 0}
        totals[key]['hours'] += hours_worked(row)
        totals[key]['days'] += 1

    for t in totals.values():
        t['hours'] = round(t['hours'], 2)

    return sorted(totals.values(), key=lambda t: t['teacher_name'])
