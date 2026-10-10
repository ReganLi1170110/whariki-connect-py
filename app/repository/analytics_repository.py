# Analytics Repository
# Backs the R/ggplot2 charts on the teacher/admin analytics dashboard
# (Sub-goal 3). Each function returns exactly the rows the corresponding R
# script expects as its input CSV - kept that narrow so the R side only ever
# has to deal with a plain "column,column" table, not raw application data.

from app.utils import get_cursor

STRAND_ORDER = ['Wellbeing', 'Belonging', 'Contribution', 'Communication', 'Exploration']


def strand_coverage(classroom=None, start_date=None, end_date=None):
    """Published learning stories per Te Whariki strand.
    classroom=None means centre-wide (Admin); otherwise scoped to one room.
    Returns every strand even if its count is zero, in canonical Te Whariki
    order, so the chart always has all five bars rather than only the
    strands that happen to have a story.
    """
    with get_cursor() as cursor:
        cursor.execute(
            """SELECT unnest(ls.strands) AS strand, COUNT(*) AS count
               FROM Learning_Stories ls
               JOIN Children c ON c.child_id = ls.child_id
               WHERE ls.status = 'published'
                 AND (%s::varchar IS NULL OR c.classroom = %s)
                 AND (%s::date IS NULL OR ls.created_at >= %s)
                 AND (%s::date IS NULL OR ls.created_at < (%s::date + interval '1 day'))
               GROUP BY strand;""",
            (classroom, classroom, start_date, start_date, end_date, end_date)
        )
        counts = {row['strand']: row['count'] for row in cursor.fetchall()}

    return [{'strand': s, 'count': counts.get(s, 0)} for s in STRAND_ORDER]


def attendance_trend(classroom=None, start_date=None, end_date=None):
    """Weekly attendance rate (% of records marked 'present') over time, so
    a dip or recovery shows up as a trend rather than a single number.
    Weeks are labelled by their Monday."""
    with get_cursor() as cursor:
        cursor.execute(
            """SELECT date_trunc('week', a.date)::date AS week_start,
                      ROUND(100.0 * COUNT(*) FILTER (WHERE a.status = 'present') / COUNT(*), 1) AS present_pct
               FROM Attendance a
               JOIN Children c ON c.child_id = a.child_id
               WHERE (%s::varchar IS NULL OR c.classroom = %s)
                 AND (%s::date IS NULL OR a.date >= %s)
                 AND (%s::date IS NULL OR a.date <= %s)
               GROUP BY week_start
               ORDER BY week_start;""",
            (classroom, classroom, start_date, start_date, end_date, end_date)
        )
        return cursor.fetchall()


def accident_frequency(classroom=None, start_date=None, end_date=None):
    """Count of submitted accident forms per injury type, most common first -
    what a teacher would actually act on (e.g. "a lot of grazes lately,
    check the playground surface")."""
    with get_cursor() as cursor:
        cursor.execute(
            """SELECT COALESCE(af.nature_of_injury, 'Unspecified') AS nature, COUNT(*) AS count
               FROM Accident_Forms af
               JOIN Children c ON c.child_id = af.child_id
               WHERE af.status = 'submitted'
                 AND (%s::varchar IS NULL OR c.classroom = %s)
                 AND (%s::date IS NULL OR af.incident_date >= %s)
                 AND (%s::date IS NULL OR af.incident_date <= %s)
               GROUP BY nature
               ORDER BY count DESC;""",
            (classroom, classroom, start_date, start_date, end_date, end_date)
        )
        return cursor.fetchall()


def routine_trend(child_id, start_date=None, end_date=None):
    """Weekly meal score (0-100, weighted All/Most/Some/None) and toileting
    issue rate (% of events that were an Accident or a Soiled nappy) for one
    child - unlike the other three charts this is inherently per-child, not
    classroom/centre scoped, since a routine record only means something
    attached to a specific child."""
    with get_cursor() as cursor:
        cursor.execute(
            """WITH meal_scores AS (
                 SELECT date_trunc('week', date)::date AS week_start,
                        AVG(CASE outcome
                              WHEN 'All' THEN 100 WHEN 'Most' THEN 66
                              WHEN 'Some' THEN 33 WHEN 'None' THEN 0
                            END) AS meal_score
                 FROM Routines
                 WHERE child_id = %s AND category = 'meal'
                   AND (%s::date IS NULL OR date >= %s)
                   AND (%s::date IS NULL OR date <= %s)
                 GROUP BY week_start
               ),
               toileting_stats AS (
                 SELECT date_trunc('week', date)::date AS week_start,
                        100.0 * COUNT(*) FILTER (WHERE outcome IN ('Accident', 'Soiled')) / COUNT(*)
                          AS toileting_issue_pct
                 FROM Routines
                 WHERE child_id = %s AND category = 'toileting'
                   AND (%s::date IS NULL OR date >= %s)
                   AND (%s::date IS NULL OR date <= %s)
                 GROUP BY week_start
               )
               SELECT COALESCE(m.week_start, t.week_start) AS week_start,
                      ROUND(COALESCE(m.meal_score, 0)::numeric, 1) AS meal_score,
                      ROUND(COALESCE(t.toileting_issue_pct, 0)::numeric, 1) AS toileting_issue_pct
               FROM meal_scores m
               FULL OUTER JOIN toileting_stats t ON m.week_start = t.week_start
               ORDER BY week_start;""",
            (child_id, start_date, start_date, end_date, end_date,
             child_id, start_date, start_date, end_date, end_date)
        )
        return cursor.fetchall()


def documentation_gaps(classroom=None, weeks=4):
    """Enrolled children with NO published learning story in the last
    `weeks` weeks, oldest last-story first (children never written about come
    first of all). This is the "documentation completion" view from the
    original proposal, requested again in UAT: teachers wanted to see which
    children have had no story for several weeks, so nobody is missed.

    Returns (gaps, total_children) so the page can say e.g. "3 of 6".
    """
    with get_cursor() as cursor:
        cursor.execute(
            """SELECT c.child_id, c.first_name, c.last_name, c.classroom,
                      MAX(ls.created_at) AS last_story_at,
                      COUNT(ls.story_id) FILTER (
                          WHERE ls.created_at >= now() - (%s * interval '1 week')
                      ) AS recent_count
               FROM Children c
               LEFT JOIN Learning_Stories ls
                      ON ls.child_id = c.child_id AND ls.status = 'published'
               WHERE c.enrolment_status = 'enrolled'
                 AND (%s::varchar IS NULL OR c.classroom = %s)
               GROUP BY c.child_id
               ORDER BY MAX(ls.created_at) ASC NULLS FIRST, c.first_name;""",
            (weeks, classroom, classroom)
        )
        rows = cursor.fetchall()
    gaps = [r for r in rows if r["recent_count"] == 0]
    return gaps, len(rows)

