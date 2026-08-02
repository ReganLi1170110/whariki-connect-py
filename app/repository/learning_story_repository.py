# Learning Story Repository

from app.utils import get_cursor


def _visibility_clause(user):
    """Parents only ever see published stories; teachers/admins see drafts too."""
    return "" if user['role'] in ('Teacher', 'Admin') else " AND ls.status = 'published'"


def list_stories_for_child(child_id, user):
    with get_cursor() as cursor:
        cursor.execute(
            f"""SELECT ls.*, u.full_name AS teacher_name,
                       c.first_name, c.last_name, c.classroom
                FROM Learning_Stories ls
                JOIN Users u ON u.user_id = ls.teacher_id
                JOIN Children c ON c.child_id = ls.child_id
                WHERE ls.child_id = %s{_visibility_clause(user)}
                ORDER BY ls.created_at DESC;""",
            (child_id,)
        )
        return cursor.fetchall()


def list_stories_for_user(user, child_id=None):
    """The main Learning Stories page:
       - Parent  -> every published story for their own children
       - Teacher -> every story they have written themselves
       - Admin   -> every story in the centre
    """
    role = user['role']
    params = []
    with get_cursor() as cursor:
        if role == 'Parent':
            sql = """SELECT ls.*, u.full_name AS teacher_name,
                            c.first_name, c.last_name, c.classroom
                     FROM Learning_Stories ls
                     JOIN Users u ON u.user_id = ls.teacher_id
                     JOIN Children c ON c.child_id = ls.child_id
                     JOIN Parent_Child pc ON pc.child_id = ls.child_id
                     WHERE pc.parent_id = %s AND ls.status = 'published'"""
            params.append(user['user_id'])
        elif role == 'Teacher':
            sql = """SELECT ls.*, u.full_name AS teacher_name,
                            c.first_name, c.last_name, c.classroom
                     FROM Learning_Stories ls
                     JOIN Users u ON u.user_id = ls.teacher_id
                     JOIN Children c ON c.child_id = ls.child_id
                     WHERE ls.teacher_id = %s"""
            params.append(user['user_id'])
        else:  # Admin
            sql = """SELECT ls.*, u.full_name AS teacher_name,
                            c.first_name, c.last_name, c.classroom
                     FROM Learning_Stories ls
                     JOIN Users u ON u.user_id = ls.teacher_id
                     JOIN Children c ON c.child_id = ls.child_id
                     WHERE 1 = 1"""

        if child_id:
            sql += " AND ls.child_id = %s"
            params.append(child_id)

        sql += " ORDER BY ls.created_at DESC;"
        cursor.execute(sql, tuple(params))
        return cursor.fetchall()


def get_story(story_id):
    with get_cursor() as cursor:
        cursor.execute(
            """SELECT ls.*, u.full_name AS teacher_name,
                      c.first_name, c.last_name, c.classroom
               FROM Learning_Stories ls
               JOIN Users u ON u.user_id = ls.teacher_id
               JOIN Children c ON c.child_id = ls.child_id
               WHERE ls.story_id = %s;""",
            (story_id,)
        )
        return cursor.fetchone()


def create_story(child_id, teacher_id, title, content, strands, outcomes,
                 valid_strands, valid_outcomes, media_url=None, status='published'):
    clean_strands = [s for s in strands if s in valid_strands]
    clean_outcomes = [o for o in outcomes if o in valid_outcomes]
    with get_cursor() as cursor:
        cursor.execute(
            """INSERT INTO Learning_Stories
                 (child_id, teacher_id, title, content, media_url, strands, outcomes, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING story_id;""",
            (child_id, teacher_id, title, content, media_url,
             clean_strands, clean_outcomes, status)
        )
        return cursor.fetchone()['story_id']


def count_for_teacher(teacher_id):
    with get_cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) AS count FROM Learning_Stories WHERE teacher_id = %s;",
            (teacher_id,)
        )
        return cursor.fetchone()['count']
