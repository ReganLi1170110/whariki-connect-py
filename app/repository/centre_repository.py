# Centre Repository

from app.utils import get_cursor


def list_centres():
    with get_cursor() as cursor:
        cursor.execute("SELECT centre_id, name FROM Centres ORDER BY name;")
        return cursor.fetchall()
