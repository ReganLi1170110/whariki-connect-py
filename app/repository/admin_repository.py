# Admin Repository

from app.utils import get_cursor


def get_stats():
    with get_cursor() as cursor:
        cursor.execute("SELECT role, COUNT(*) AS count FROM Users GROUP BY role;")
        users_by_role = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) AS count FROM Children WHERE enrolment_status = 'enrolled';")
        total_children = cursor.fetchone()['count']

        cursor.execute(
            """SELECT status, COUNT(*) AS count FROM Attendance
               WHERE date = CURRENT_DATE GROUP BY status;"""
        )
        today_attendance = cursor.fetchall()

        cursor.execute(
            """SELECT
                 COUNT(*) AS total,
                 COUNT(*) FILTER (WHERE notifiable_event) AS notifiable,
                 COUNT(*) FILTER (WHERE parent_acknowledged_at IS NULL) AS unacknowledged
               FROM Accident_Forms;"""
        )
        accident_stats = cursor.fetchone()

        cursor.execute("SELECT COUNT(*) AS count FROM Learning_Stories;")
        total_stories = cursor.fetchone()['count']

    return {
        'users_by_role': users_by_role,
        'total_children': total_children,
        'today_attendance': today_attendance,
        'accident_stats': accident_stats,
        'total_stories': total_stories,
    }


def list_all_users(search=None, role=None, status=None):
    """Staff & families table on the admin panel. All three filters are
    optional: `search` matches name or email (case-insensitive), `role` and
    `status` must match exactly."""
    sql = """SELECT user_id, role, full_name, email, phone, classroom, status, created_at
             FROM Users WHERE 1 = 1"""
    params = []
    if search:
        sql += " AND (full_name ILIKE %s OR email ILIKE %s)"
        like = f"%{search}%"
        params += [like, like]
    if role:
        sql += " AND role = %s"
        params.append(role)
    if status:
        sql += " AND status = %s"
        params.append(status)
    sql += " ORDER BY role, full_name;"
    with get_cursor() as cursor:
        cursor.execute(sql, tuple(params))
        return cursor.fetchall()
