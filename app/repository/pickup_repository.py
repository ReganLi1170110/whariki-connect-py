# Authorized Pickups Repository
# Who besides the registered parents may collect a child - separate from
# emergency_contact (a single name for emergencies), this is a proper list
# staff can check against at pickup time.

from app.utils import get_cursor


def list_for_child(child_id):
    with get_cursor() as cursor:
        cursor.execute(
            """SELECT ap.*, u.full_name AS added_by_name
               FROM Authorized_Pickups ap
               LEFT JOIN Users u ON u.user_id = ap.added_by
               WHERE ap.child_id = %s
               ORDER BY ap.created_at;""",
            (child_id,)
        )
        return cursor.fetchall()


def add_pickup_person(child_id, full_name, phone, relationship, notes, added_by):
    with get_cursor() as cursor:
        cursor.execute(
            """INSERT INTO Authorized_Pickups
                 (child_id, full_name, phone, relationship, notes, added_by)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING pickup_id;""",
            (child_id, full_name, phone, relationship, notes, added_by)
        )
        return cursor.fetchone()['pickup_id']


def delete_pickup_person(pickup_id, child_id):
    """Scoped by child_id, matching the pattern used for every other
    per-child delete in this codebase - so a stale/guessed id can't be
    used to remove a different child's entry."""
    with get_cursor() as cursor:
        cursor.execute(
            "DELETE FROM Authorized_Pickups WHERE pickup_id = %s AND child_id = %s;",
            (pickup_id, child_id)
        )
