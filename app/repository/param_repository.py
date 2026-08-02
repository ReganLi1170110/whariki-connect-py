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
