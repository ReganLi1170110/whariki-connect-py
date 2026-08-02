# Accident Form Repository

from app.utils import get_cursor

# Columns shared by every accident-form query.
_SELECT = """SELECT af.*, u.full_name AS teacher_name,
                    c.first_name, c.last_name, c.classroom
             FROM Accident_Forms af
             JOIN Users u ON u.user_id = af.teacher_id
             JOIN Children c ON c.child_id = af.child_id"""


def list_for_child(child_id, user=None):
    """Parents only see submitted forms; teachers/admins also see their drafts."""
    extra = ""
    if user and user['role'] == 'Parent':
        extra = " AND af.status = 'submitted'"
    with get_cursor() as cursor:
        cursor.execute(
            f"{_SELECT} WHERE af.child_id = %s{extra} ORDER BY af.incident_date DESC, af.created_at DESC;",
            (child_id,)
        )
        return cursor.fetchall()


def list_for_user(user):
    """The main Accident Forms page:
       - Parent  -> submitted forms for their own children
       - Teacher -> forms they filed, plus any form for a child in their room
       - Admin   -> everything
    """
    role = user['role']
    with get_cursor() as cursor:
        if role == 'Parent':
            cursor.execute(
                f"""{_SELECT}
                    JOIN Parent_Child pc ON pc.child_id = af.child_id
                    WHERE pc.parent_id = %s AND af.status = 'submitted'
                    ORDER BY af.incident_date DESC, af.created_at DESC;""",
                (user['user_id'],)
            )
        elif role == 'Teacher':
            cursor.execute(
                f"""{_SELECT}
                    WHERE c.classroom = %s
                    ORDER BY af.incident_date DESC, af.created_at DESC;""",
                (user['classroom'],)
            )
        else:
            cursor.execute(
                f"{_SELECT} ORDER BY af.incident_date DESC, af.created_at DESC;"
            )
        return cursor.fetchall()


def get_accident(accident_id):
    with get_cursor() as cursor:
        cursor.execute(f"{_SELECT} WHERE af.accident_id = %s;", (accident_id,))
        return cursor.fetchone()


def create_accident_form(data):
    """`data` is a plain dict built by the route from the submitted form."""
    with get_cursor() as cursor:
        cursor.execute(
            """INSERT INTO Accident_Forms
                 (child_id, teacher_id, incident_date, incident_time, location,
                  nature_of_injury, body_part, description, action_taken,
                  additional_information, parent_contacted, parent_contacted_name,
                  contacted_by, contact_method, contact_method_other,
                  parent_contacted_time, other_actions_taken,
                  medical_attention_needed, notifiable_event, status,
                  provider_signature, teacher_signed_at)
               VALUES (%(child_id)s, %(teacher_id)s, %(incident_date)s, %(incident_time)s,
                       %(location)s, %(nature_of_injury)s, %(body_part)s, %(description)s,
                       %(action_taken)s, %(additional_information)s, %(parent_contacted)s,
                       %(parent_contacted_name)s, %(contacted_by)s, %(contact_method)s,
                       %(contact_method_other)s, %(parent_contacted_time)s,
                       %(other_actions_taken)s, %(medical_attention_needed)s,
                       %(notifiable_event)s, %(status)s, %(provider_signature)s,
                       %(teacher_signed_at)s)
               RETURNING accident_id;""",
            data
        )
        return cursor.fetchone()['accident_id']


def acknowledge(accident_id, parent_id):
    """Only lets a parent linked to the child acknowledge a submitted form."""
    with get_cursor() as cursor:
        cursor.execute(
            """SELECT af.accident_id FROM Accident_Forms af
               JOIN Parent_Child pc ON pc.child_id = af.child_id
               WHERE af.accident_id = %s AND pc.parent_id = %s
                 AND af.status = 'submitted';""",
            (accident_id, parent_id)
        )
        if cursor.fetchone() is None:
            return False

        cursor.execute(
            """UPDATE Accident_Forms
               SET parent_acknowledged_at = now(), parent_acknowledged_by = %s
               WHERE accident_id = %s;""",
            (parent_id, accident_id)
        )
        return True
