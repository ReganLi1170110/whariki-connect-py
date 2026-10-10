# Child Repository
# Handles data access for child profiles, and the role-based access checks
# that decide which children a given user is allowed to see.

from app.utils import get_cursor


def list_children_for_user(user, include_withdrawn=False):
    """Returns the children visible to the given user (a dict-like row
    from Users, or the session values for role/user_id/classroom).
    Withdrawn children are hidden by default everywhere - a Teacher or
    Parent never needs to see them, and even Admin only sees them when
    include_withdrawn is explicitly set (e.g. a "show withdrawn" toggle)."""
    role = user['role']
    status_clause = "" if include_withdrawn else "AND c.enrolment_status = 'enrolled'"

    with get_cursor() as cursor:
        if role == 'Admin':
            cursor.execute(
                f"""SELECT * FROM Children c WHERE 1=1 {status_clause}
                    ORDER BY classroom, last_name;"""
            )
        elif role == 'Teacher':
            cursor.execute(
                f"""SELECT * FROM Children c
                    WHERE c.classroom = %s {status_clause}
                    ORDER BY c.last_name;""",
                (user['classroom'],)
            )
        else:  # Parent
            cursor.execute(
                f"""SELECT c.* FROM Children c
                    JOIN Parent_Child pc ON pc.child_id = c.child_id
                    WHERE pc.parent_id = %s {status_clause}
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


def link_parents_to_child(child_id, parent_ids, relationship='parent'):
    """The inverse of link_parent_to_children - used when creating a new
    child and linking it to one or more already-approved parent accounts
    in the same step."""
    if not parent_ids:
        return
    with get_cursor() as cursor:
        for parent_id in parent_ids:
            cursor.execute(
                """INSERT INTO Parent_Child (parent_id, child_id, relationship)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (parent_id, child_id) DO NOTHING;""",
                (parent_id, child_id, relationship)
            )


def update_basic_info(child_id, first_name, last_name, date_of_birth, classroom):
    """Name, date of birth and classroom - the fields only settable at
    creation time until now. Separate from update_health_info /
    update_child_avatar / update_child_emergency_contact, which already
    have their own edit paths elsewhere."""
    with get_cursor() as cursor:
        cursor.execute(
            """UPDATE Children
               SET first_name = %s, last_name = %s, date_of_birth = %s, classroom = %s
               WHERE child_id = %s;""",
            (first_name, last_name, date_of_birth, classroom, child_id)
        )


def update_health_info(child_id, allergies, medical_conditions, medications,
                       dietary_requirements, medical_notes):
    """Health & safety fields, editable by teachers/admins (and by the
    child's own parent from their profile page - see profile_repository)."""
    with get_cursor() as cursor:
        cursor.execute(
            """UPDATE Children
               SET allergies = %s, medical_conditions = %s, medications = %s,
                   dietary_requirements = %s, medical_notes = %s
               WHERE child_id = %s;""",
            (allergies, medical_conditions, medications,
             dietary_requirements, medical_notes, child_id)
        )


def list_all_children_basic():
    """Simple id/name list for the admin approval screen's child picker."""
    with get_cursor() as cursor:
        cursor.execute(
            "SELECT child_id, first_name, last_name, classroom FROM Children ORDER BY last_name;"
        )
        return cursor.fetchall()


def withdraw_child(child_id, withdrawal_date, notes=None):
    """Marks a child as no longer enrolled. Never deletes anything - their
    learning stories, attendance, accident forms etc. all stay exactly as
    they are, just hidden from the default lists from here on."""
    with get_cursor() as cursor:
        cursor.execute(
            """UPDATE Children
               SET enrolment_status = 'withdrawn', withdrawal_date = %s, withdrawal_notes = %s
               WHERE child_id = %s;""",
            (withdrawal_date, notes, child_id)
        )


def reenrol_child(child_id):
    """Undoes a withdrawal - either it was a mistake, or the child has
    come back to the centre."""
    with get_cursor() as cursor:
        cursor.execute(
            """UPDATE Children
               SET enrolment_status = 'enrolled', withdrawal_date = NULL, withdrawal_notes = NULL
               WHERE child_id = %s;""",
            (child_id,)
        )


def create_child(first_name, last_name, date_of_birth, classroom,
                 emergency_contact=None, emergency_phone=None,
                 allergies=None, medical_conditions=None, medications=None,
                 dietary_requirements=None, medical_notes=None, avatar_url=None):
    """Admin-only: registers a brand-new child. Everything except the four
    required fields (name, DOB, classroom) can be filled in now or added
    later from the child's own profile page."""
    with get_cursor() as cursor:
        cursor.execute(
            """INSERT INTO Children
                 (first_name, last_name, date_of_birth, classroom,
                  emergency_contact, emergency_phone,
                  allergies, medical_conditions, medications,
                  dietary_requirements, medical_notes, avatar_url)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               RETURNING child_id;""",
            (first_name, last_name, date_of_birth, classroom,
             emergency_contact, emergency_phone,
             allergies, medical_conditions, medications,
             dietary_requirements, medical_notes, avatar_url)
        )
        return cursor.fetchone()['child_id']


def list_approved_parents():
    """For the admin's 'link to parent(s)' picker when creating a child."""
    with get_cursor() as cursor:
        cursor.execute(
            """SELECT user_id, full_name, email FROM Users
               WHERE role = 'Parent' AND status = 'approved'
               ORDER BY full_name;"""
        )
        return cursor.fetchall()
