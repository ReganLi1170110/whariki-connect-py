# Immunization Repository
# NZ National Immunisation Schedule records per child. Teachers/admins record
# and maintain these (usually transcribed from a parent's Well Child book);
# parents can view their own children's records only.

from app.utils import get_cursor

# Mirrors the NZ National Immunisation Schedule milestones closely enough
# for a centre to track against - not a substitute for the Well Child book.
VACCINE_CATALOG = [
    'Rotavirus', 'DTaP-IPV-Hib-HepB (6-in-1)', 'PCV13 (Pneumococcal)',
    'MMR (Measles, Mumps, Rubella)', 'Varicella (Chickenpox)',
    'Hib booster', 'DTaP-IPV (4-in-1 booster)', 'Influenza (annual)',
    'Meningococcal B', 'Other',
]
DOSE_LABELS = [
    '6 weeks', '3 months', '5 months', '12 months', '15 months',
    '4 years', 'Booster', 'Annual', 'Other',
]
STATUSES = ['completed', 'scheduled', 'overdue', 'exempt']


def list_for_child(child_id):
    """Newest first isn't as useful here as schedule order, so this sorts
    by date_given (nulls - i.e. not-yet-given doses - last)."""
    with get_cursor() as cursor:
        cursor.execute(
            """SELECT i.*, u.full_name AS recorded_by_name
               FROM Immunizations i
               LEFT JOIN Users u ON u.user_id = i.recorded_by
               WHERE i.child_id = %s
               ORDER BY i.date_given ASC NULLS LAST, i.created_at ASC;""",
            (child_id,)
        )
        return cursor.fetchall()


def create_immunization(child_id, recorded_by, vaccine_name, dose_label,
                        date_given, status, notes=None):
    with get_cursor() as cursor:
        cursor.execute(
            """INSERT INTO Immunizations
                 (child_id, recorded_by, vaccine_name, dose_label,
                  date_given, status, notes)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               RETURNING immunization_id;""",
            (child_id, recorded_by, vaccine_name, dose_label,
             date_given, status, notes)
        )
        return cursor.fetchone()['immunization_id']


def delete_immunization(immunization_id, child_id):
    """Scoped by child_id so a teacher can't delete a record by guessing an id."""
    with get_cursor() as cursor:
        cursor.execute(
            "DELETE FROM Immunizations WHERE immunization_id = %s AND child_id = %s;",
            (immunization_id, child_id)
        )


def summary_for_child(child_id):
    """Quick counts for a status badge: how many doses are overdue, etc."""
    with get_cursor() as cursor:
        cursor.execute(
            """SELECT status, COUNT(*)::int AS count
               FROM Immunizations WHERE child_id = %s GROUP BY status;""",
            (child_id,)
        )
        return {row['status']: row['count'] for row in cursor.fetchall()}
