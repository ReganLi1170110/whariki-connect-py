# Notification Repository

from app.utils import get_cursor


def list_for_user(user_id, limit=50):
    with get_cursor() as cursor:
        cursor.execute(
            """SELECT * FROM Notifications WHERE user_id = %s
               ORDER BY created_at DESC LIMIT %s;""",
            (user_id, limit)
        )
        return cursor.fetchall()


def count_unread(user_id):
    with get_cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) AS count FROM Notifications WHERE user_id = %s AND is_read = false;",
            (user_id,)
        )
        return cursor.fetchone()['count']


def create(user_id, notif_type, content, related_id=None):
    with get_cursor() as cursor:
        cursor.execute(
            """INSERT INTO Notifications (user_id, type, content, related_id)
               VALUES (%s, %s, %s, %s);""",
            (user_id, notif_type, content, related_id)
        )


def create_for_parents_of_child(child_id, notif_type, content, related_id=None):
    """Convenience helper: notify every parent linked to a given child."""
    with get_cursor() as cursor:
        cursor.execute("SELECT parent_id FROM Parent_Child WHERE child_id = %s;", (child_id,))
        parent_ids = [row['parent_id'] for row in cursor.fetchall()]
        for parent_id in parent_ids:
            cursor.execute(
                """INSERT INTO Notifications (user_id, type, content, related_id)
                   VALUES (%s, %s, %s, %s);""",
                (parent_id, notif_type, content, related_id)
            )


def mark_read(notification_id, user_id):
    with get_cursor() as cursor:
        cursor.execute(
            """UPDATE Notifications SET is_read = true
               WHERE notification_id = %s AND user_id = %s;""",
            (notification_id, user_id)
        )
