# Param Repository
# Reads static lookup/reference data (classrooms, curriculum strands, etc.)
# that is populated once by populate_database.sql.

from app.utils import get_cursor


def get_param_values(param_type):
    """Returns the list of active param_value strings for a given param_type,
    e.g. get_param_values('curriculum_strand') -> ['Wellbeing', 'Belonging', ...]
    """
    with get_cursor() as cursor:
        cursor.execute(
            """SELECT param_value FROM Params
               WHERE param_type = %s AND status = 'Active'
               ORDER BY id;""",
            (param_type,)
        )
        return [row['param_value'] for row in cursor.fetchall()]


def get_classrooms():
    return get_param_values('classroom')


def get_curriculum_strands():
    return get_param_values('curriculum_strand')


def get_accident_body_parts():
    return get_param_values('accident_body_part')


def get_injury_natures():
    return get_param_values('injury_nature')


def get_contact_methods():
    return get_param_values('contact_method')


def get_learning_outcomes_by_strand():
    """Returns an ordered dict-like list of (strand, [outcomes]) so the
    learning story form can show each strand's outcomes grouped together."""
    with get_cursor() as cursor:
        cursor.execute(
            """SELECT param_value, description FROM Params
               WHERE param_type = 'learning_outcome' AND status = 'Active'
               ORDER BY id;"""
        )
        rows = cursor.fetchall()

    grouped = {}
    for row in rows:
        grouped.setdefault(row['description'], []).append(row['param_value'])
    return grouped


def get_all_learning_outcomes():
    return get_param_values('learning_outcome')


# --- Admin management -------------------------------------------------------
# Only these types are safe to manage through the UI: they're pure lookup
# data with no other code depending on the exact set of values. classroom
# is separately checked for use before deactivation, since children/teachers
# reference it by name; the others are copied as free text into records at
# submission time, so removing one as a future option never touches history.
EDITABLE_PARAM_TYPES = [
    'classroom', 'injury_nature', 'accident_body_part',
    'contact_method', 'learning_outcome',
]

# Shown read-only, with an explanation of why: curriculum_strand is fixed by
# the Te Whariki framework and is also hard-coded into the analytics chart
# (STRAND_ORDER), so editing it here would silently desync the two.
# attendance_status is enforced by a database CHECK constraint on the
# Attendance table itself, independent of this list - editing it here
# wouldn't actually change what the app accepts.
READONLY_PARAM_TYPES = ['curriculum_strand', 'attendance_status']


def list_all_params_by_type(param_type):
    """Every value for a type, active AND inactive, for the admin
    management page - unlike get_param_values, which only returns active
    ones for use in the rest of the app."""
    with get_cursor() as cursor:
        cursor.execute(
            "SELECT * FROM Params WHERE param_type = %s ORDER BY status DESC, id;",
            (param_type,)
        )
        return cursor.fetchall()


def add_param(param_type, param_value, description=None):
    with get_cursor() as cursor:
        cursor.execute(
            """INSERT INTO Params (param_type, param_value, status, description)
               VALUES (%s, %s, 'Active', %s) RETURNING id;""",
            (param_type, param_value, description)
        )
        return cursor.fetchone()['id']


def get_param_by_id(param_id):
    with get_cursor() as cursor:
        cursor.execute("SELECT * FROM Params WHERE id = %s;", (param_id,))
        return cursor.fetchone()


def deactivate_param(param_id):
    with get_cursor() as cursor:
        cursor.execute("UPDATE Params SET status = 'Inactive' WHERE id = %s;", (param_id,))


def reactivate_param(param_id):
    with get_cursor() as cursor:
        cursor.execute("UPDATE Params SET status = 'Active' WHERE id = %s;", (param_id,))


def classroom_in_use(classroom_name):
    """How many children and staff currently reference this classroom by
    name - checked before letting an admin deactivate it, since classroom
    is stored as plain text on Children/Users rather than a foreign key."""
    with get_cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) AS count FROM Children WHERE classroom = %s AND enrolment_status = 'enrolled';",
            (classroom_name,)
        )
        children_count = cursor.fetchone()['count']
        cursor.execute(
            "SELECT COUNT(*) AS count FROM Users WHERE classroom = %s AND status = 'approved';",
            (classroom_name,)
        )
        staff_count = cursor.fetchone()['count']
        return children_count + staff_count
