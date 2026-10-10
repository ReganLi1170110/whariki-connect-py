# Message Repository
# Parent <-> teacher chat, optionally scoped to a specific child.

from app.utils import get_cursor


def list_contacts_for_user(user):
    """Who this user is allowed to message:
       - parent -> the teacher(s) of their children
       - teacher -> the parents of children in their classroom
       - admin -> everyone (for support purposes)
    """
    role = user['role']
    with get_cursor() as cursor:
        if role == 'Parent':
            # A teacher is staff, never "bound" to a child. child_id is still
            # selected because it scopes the message thread, but the UI labels
            # these rows with the teacher's room instead of a child's name.
            cursor.execute(
                """SELECT DISTINCT u.user_id, u.full_name, u.classroom, u.avatar_url,
                          c.child_id, c.first_name AS child_first_name
                   FROM Users u
                   JOIN Children c ON c.classroom = u.classroom
                   JOIN Parent_Child pc ON pc.child_id = c.child_id
                   WHERE u.role = 'Teacher' AND pc.parent_id = %s
                   ORDER BY u.full_name;""",
                (user['user_id'],)
            )
        elif role == 'Teacher':
            cursor.execute(
                """SELECT DISTINCT u.user_id, u.full_name, NULL AS classroom, u.avatar_url,
                          c.child_id, c.first_name AS child_first_name
                   FROM Users u
                   JOIN Parent_Child pc ON pc.parent_id = u.user_id
                   JOIN Children c ON c.child_id = pc.child_id
                   WHERE u.role = 'Parent' AND c.classroom = %s;""",
                (user['classroom'],)
            )
        else:  # Admin
            cursor.execute(
                """SELECT user_id, full_name, role, classroom, avatar_url,
                          NULL AS child_id, NULL AS child_first_name
                   FROM Users WHERE user_id != %s ORDER BY full_name;""",
                (user['user_id'],)
            )
        return cursor.fetchall()


def list_thread(user_id, other_user_id, child_id=None):
    with get_cursor() as cursor:
        if child_id:
            # `OR m.child_id IS NULL` keeps any older messages that were sent
            # before the thread was scoped to a specific child visible.
            cursor.execute(
                """SELECT m.*, s.full_name AS sender_name
                   FROM Messages m JOIN Users s ON s.user_id = m.sender_id
                   WHERE ((m.sender_id = %s AND m.receiver_id = %s)
                       OR (m.sender_id = %s AND m.receiver_id = %s))
                     AND (m.child_id = %s OR m.child_id IS NULL)
                   ORDER BY m.created_at ASC;""",
                (user_id, other_user_id, other_user_id, user_id, child_id)
            )
        else:
            cursor.execute(
                """SELECT m.*, s.full_name AS sender_name
                   FROM Messages m JOIN Users s ON s.user_id = m.sender_id
                   WHERE (m.sender_id = %s AND m.receiver_id = %s)
                      OR (m.sender_id = %s AND m.receiver_id = %s)
                   ORDER BY m.created_at ASC;""",
                (user_id, other_user_id, other_user_id, user_id)
            )
        return cursor.fetchall()


def send_message(sender_id, receiver_id, content, child_id=None):
    with get_cursor() as cursor:
        cursor.execute(
            """INSERT INTO Messages (sender_id, receiver_id, child_id, content)
               VALUES (%s, %s, %s, %s) RETURNING message_id;""",
            (sender_id, receiver_id, child_id, content)
        )
        return cursor.fetchone()['message_id']


def send_broadcast_copy(sender_id, receiver_id, content, broadcast_id):
    """One recipient's copy of an announcement - same Messages table, just
    tagged so the chat UI can style it as a broadcast rather than a DM."""
    with get_cursor() as cursor:
        cursor.execute(
            """INSERT INTO Messages (sender_id, receiver_id, content, is_broadcast, broadcast_id)
               VALUES (%s, %s, %s, true, %s) RETURNING message_id;""",
            (sender_id, receiver_id, content, broadcast_id)
        )
        return cursor.fetchone()['message_id']


def unread_counts_by_sender(user_id):
    """Returns {sender_id: unread_count} so the contact list can show a red
    dot next to the people who have messaged you and not been read yet."""
    with get_cursor() as cursor:
        cursor.execute(
            """SELECT sender_id, COUNT(*) AS count
               FROM Messages
               WHERE receiver_id = %s AND is_read = false
               GROUP BY sender_id;""",
            (user_id,)
        )
        return {row['sender_id']: row['count'] for row in cursor.fetchall()}


def count_unread(user_id):
    """Total unread messages, used for the sidebar badge."""
    with get_cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) AS count FROM Messages WHERE receiver_id = %s AND is_read = false;",
            (user_id,)
        )
        return cursor.fetchone()['count']


def mark_thread_read(user_id, other_user_id, child_id=None):
    """Marks every message the other person sent in this thread as read.
    Called when the thread is opened."""
    with get_cursor() as cursor:
        if child_id:
            cursor.execute(
                """UPDATE Messages SET is_read = true
                   WHERE receiver_id = %s AND sender_id = %s
                     AND (child_id = %s OR child_id IS NULL)
                     AND is_read = false;""",
                (user_id, other_user_id, child_id)
            )
        else:
            cursor.execute(
                """UPDATE Messages SET is_read = true
                   WHERE receiver_id = %s AND sender_id = %s AND is_read = false;""",
                (user_id, other_user_id)
            )


def search_messages(user_id, query, other_user_id=None, child_id=None):
    """Full-text-ish search across every message this user sent or received.
    `query` is matched case-insensitively against the message body. When
    other_user_id/child_id are supplied the search is limited to that thread."""
    like = f"%{query}%"
    sql = """SELECT m.*, s.full_name AS sender_name, r.full_name AS receiver_name,
                    c.first_name AS child_first_name
             FROM Messages m
             JOIN Users s ON s.user_id = m.sender_id
             JOIN Users r ON r.user_id = m.receiver_id
             LEFT JOIN Children c ON c.child_id = m.child_id
             WHERE (m.sender_id = %s OR m.receiver_id = %s)
               AND m.content ILIKE %s"""
    params = [user_id, user_id, like]

    if other_user_id:
        sql += " AND (m.sender_id = %s OR m.receiver_id = %s)"
        params.extend([other_user_id, other_user_id])
    if child_id:
        sql += " AND m.child_id = %s"
        params.append(child_id)

    sql += " ORDER BY m.created_at DESC LIMIT 60;"

    with get_cursor() as cursor:
        cursor.execute(sql, tuple(params))
        return cursor.fetchall()
