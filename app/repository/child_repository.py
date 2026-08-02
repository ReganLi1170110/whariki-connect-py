# Child Repository
# Handles data access for child profiles, and the role-based access checks
# that decide which children a given user is allowed to see.

from app.utils import get_cursor


def list_children_for_user(user):
    """Returns the children visible to the given user (a dict-like row
    from Users, or the session values for role/user_id/classroom)."""
    role = user['role']

    with get_cursor() as cursor:
        if role == 'Admin':
            cursor.execute(
                """SELECT * FROM Children ORDER BY classroom, last_name;"""
            )
        elif role == 'Teacher':
            cursor.execute(
                """SELECT c.* FROM Children c
                   WHERE c.classroom = %s
                   ORDER BY c.last_name;""",
                (user['classroom'],)
            )
        else:  # Parent
            cursor.execute(
                """SELECT c.* FROM Children c
                   JOIN Parent_Child pc ON pc.child_id = c.child_id
                   WHERE pc.parent_id = %s
                   ORDER BY c.last_name;""",
                (user['user_id'],)
            )
        return cursor.fetchall()


def can_access_child(user, child_id):
    """Server-side access check - never rely on the UI alone to hide data."""
    role = user['role']
    if role == 'Admin':
        return True

    with get_cursor() as cursor:
        if role == 'Teacher':
            cursor.execute(
                """SELECT 1 FROM Children WHERE child_id = %s AND classroom = %s;""",
                (child_id, user['classroom'])
            )
        else:  # Parent
            cursor.execute(
                """SELECT 1 FROM Parent_Child WHERE parent_id = %s AND child_id = %s;""",
                (user['user_id'], child_id)
            )
        return cursor.fetchone() is not None


def get_child_by_id(child_id):
    with get_cursor() as cursor:
        cursor.execute("SELECT * FROM Children WHERE child_id = %s;", (child_id,))
        return cursor.fetchone()


def get_parents_for_child(child_id):
    with get_cursor() as cursor:
        cursor.execute(
            """SELECT u.user_id, u.full_name, u.email, u.phone, pc.relationship
               FROM Parent_Child pc JOIN Users u ON u.user_id = pc.parent_id
               WHERE pc.child_id = %s;""",
            (child_id,)
        )
        return cursor.fetchall()


def link_parent_to_children(parent_id, child_ids, relationship='parent'):
    """Used by the admin approval screen: after approving a self-registered
    parent, the admin picks which child/children to link them to, since a
    new sign-up has no automatic connection to any child yet."""
    if not child_ids:
        return
    with get_cursor() as cursor:
        for child_id in child_ids:
            cursor.execute(
                """INSERT INTO Parent_Child (parent_id, child_id, relationship)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (parent_id, child_id) DO NOTHING;""",
                (parent_id, child_id, relationship)
            )


def list_all_children_basic():
    """Simple id/name list for the admin approval screen's child picker."""
    with get_cursor() as cursor:
        cursor.execute(
            "SELECT child_id, first_name, last_name, classroom FROM Children ORDER BY last_name;"
        )
        return cursor.fetchall()
