# Profile Repository
# A user maintains their own details; a parent additionally maintains the
# details of children they are linked to.

from app.utils import get_cursor


def get_profile(user_id):
    with get_cursor() as cursor:
        cursor.execute(
            """SELECT u.user_id, u.role, u.full_name, u.email, u.phone,
                      u.classroom, u.avatar_url, u.created_at, c.name AS centre_name
               FROM Users u
               LEFT JOIN Centres c ON c.centre_id = u.centre_id
               WHERE u.user_id = %s;""",
            (user_id,)
        )
        return cursor.fetchone()


def update_own_details(user_id, full_name, phone):
    with get_cursor() as cursor:
        cursor.execute(
            "UPDATE Users SET full_name = %s, phone = %s WHERE user_id = %s;",
            (full_name, phone, user_id)
        )


def update_own_avatar(user_id, avatar_url):
    with get_cursor() as cursor:
        cursor.execute("UPDATE Users SET avatar_url = %s WHERE user_id = %s;",
                       (avatar_url, user_id))


def list_own_children(parent_id):
    """Children this parent is linked to - the only ones they may edit."""
    with get_cursor() as cursor:
        cursor.execute(
            """SELECT c.child_id, c.first_name, c.last_name, c.classroom,
                      c.emergency_contact, c.emergency_phone, c.avatar_url,
                      c.allergies, c.medical_conditions, c.medications,
                      c.dietary_requirements, c.medical_notes
               FROM Children c
               JOIN Parent_Child pc ON pc.child_id = c.child_id
               WHERE pc.parent_id = %s
               ORDER BY c.first_name;""",
            (parent_id,)
        )
        return cursor.fetchall()


def parent_owns_child(parent_id, child_id):
    with get_cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM Parent_Child WHERE parent_id = %s AND child_id = %s;",
            (parent_id, child_id)
        )
        return cursor.fetchone() is not None


def update_child_emergency_contact(child_id, emergency_contact, emergency_phone):
    with get_cursor() as cursor:
        cursor.execute(
            """UPDATE Children SET emergency_contact = %s, emergency_phone = %s
               WHERE child_id = %s;""",
            (emergency_contact, emergency_phone, child_id)
        )


def update_child_health_info(child_id, allergies, medical_conditions, medications,
                             dietary_requirements, medical_notes):
    with get_cursor() as cursor:
        cursor.execute(
            """UPDATE Children
               SET allergies = %s, medical_conditions = %s, medications = %s,
                   dietary_requirements = %s, medical_notes = %s
               WHERE child_id = %s;""",
            (allergies, medical_conditions, medications,
             dietary_requirements, medical_notes, child_id)
        )


def update_child_avatar(child_id, avatar_url):
    with get_cursor() as cursor:
        cursor.execute("UPDATE Children SET avatar_url = %s WHERE child_id = %s;",
                       (avatar_url, child_id))
