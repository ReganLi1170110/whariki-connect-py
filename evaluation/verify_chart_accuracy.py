"""Chart accuracy check against the full seeded database.

The analytics charts are drawn from the numbers returned by
app/repository/analytics_repository.py (aggregated in SQL). This script pulls
the RAW rows instead and recomputes every chart value independently in plain
Python, then compares the two, classroom by classroom. Any difference is
printed. This is the "manual verification of chart accuracy against
hand-calculated values" from the proposal, done for every data point
rather than a sample.

Usage (from the project root):
    python evaluation/verify_chart_accuracy.py
"""
import os
import sys
from collections import Counter, defaultdict
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import flask_app  # noqa: E402
from app.repository import analytics_repository  # noqa: E402
from app.utils import get_cursor  # noqa: E402


def raw(query, params=()):
    with get_cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchall()


def round1(x):
    """Round half away from zero, like PostgreSQL's ROUND() - Python's built-in
    round() uses banker's rounding (31.25 -> 31.2), which would report false
    0.1 differences on exact .x5 values."""
    return float(Decimal(str(x)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def monday(d):
    return d - timedelta(days=d.weekday())


def main():
    checked = mismatches = 0
    with flask_app.test_request_context():
        rooms = [r["classroom"] for r in raw("SELECT DISTINCT classroom FROM Children ORDER BY classroom;")]
        for room in rooms + [None]:
            label = room or "Whole centre"

            # --- Strand coverage ---
            stories = raw("""SELECT ls.strands FROM Learning_Stories ls JOIN Children c USING (child_id)
                             WHERE ls.status = 'published' AND (%s::varchar IS NULL OR c.classroom = %s);""",
                          (room, room))
            expected = Counter(s for row in stories for s in row["strands"])
            for row in analytics_repository.strand_coverage(room):
                checked += 1
                if row["count"] != expected.get(row["strand"], 0):
                    mismatches += 1
                    print(f"[{label}] strand {row['strand']}: chart {row['count']} vs raw {expected.get(row['strand'], 0)}")

            # --- Weekly attendance rate ---
            att = raw("""SELECT a.date, a.status FROM Attendance a JOIN Children c USING (child_id)
                         WHERE (%s::varchar IS NULL OR c.classroom = %s);""", (room, room))
            weeks = defaultdict(lambda: [0, 0])
            for r in att:
                w = weeks[monday(r["date"])]
                w[1] += 1
                w[0] += r["status"] == "present"
            chart = analytics_repository.attendance_trend(room)
            for row in chart:
                present, total = weeks[row["week_start"]]
                expected_pct = round1(100.0 * present / total)
                checked += 1
                if abs(float(row["present_pct"]) - expected_pct) > 0.05:
                    mismatches += 1
                    print(f"[{label}] week {row['week_start']}: chart {row['present_pct']} vs raw {expected_pct}")
            if len(chart) != len(weeks):
                mismatches += 1
                print(f"[{label}] week count differs: chart {len(chart)} vs raw {len(weeks)}")

            # --- Accident frequency ---
            forms = raw("""SELECT COALESCE(af.nature_of_injury, 'Unspecified') AS nature
                           FROM Accident_Forms af JOIN Children c USING (child_id)
                           WHERE af.status = 'submitted' AND (%s::varchar IS NULL OR c.classroom = %s);""",
                        (room, room))
            expected = Counter(r["nature"] for r in forms)
            chart = {r["nature"]: r["count"] for r in analytics_repository.accident_frequency(room)}
            checked += 1
            if chart != dict(expected):
                mismatches += 1
                print(f"[{label}] accident counts differ: chart {chart} vs raw {dict(expected)}")

            print(f"{label:<18} stories={len(stories):>3}  attendance rows={len(att):>5}  "
                  f"weeks={len(weeks):>2}  accident forms={len(forms):>2}")

        # --- Routine trend (per child) ---
        weights = {"All": 100, "Most": 66, "Some": 33, "None": 0}
        children = raw("SELECT child_id FROM Children ORDER BY child_id;")
        for child in children:
            rows = raw("SELECT date, category, outcome FROM Routines WHERE child_id = %s;", (child["child_id"],))
            meals, toilets = defaultdict(list), defaultdict(list)
            for r in rows:
                if r["category"] == "meal":
                    meals[monday(r["date"])].append(weights[r["outcome"]])
                else:
                    toilets[monday(r["date"])].append(r["outcome"] in ("Accident", "Soiled"))
            for row in analytics_repository.routine_trend(child["child_id"]):
                w = row["week_start"]
                exp_meal = round1(sum(meals[w]) / len(meals[w])) if meals[w] else 0
                exp_toilet = round1(100.0 * sum(toilets[w]) / len(toilets[w])) if toilets[w] else 0
                checked += 2
                if abs(float(row["meal_score"]) - exp_meal) > 0.05:
                    mismatches += 1
                    print(f"child {child['child_id']} week {w}: meal {row['meal_score']} vs raw {exp_meal}")
                if abs(float(row["toileting_issue_pct"]) - exp_toilet) > 0.05:
                    mismatches += 1
                    print(f"child {child['child_id']} week {w}: toileting {row['toileting_issue_pct']} vs raw {exp_toilet}")
        print(f"Routine trend checked for {len(children)} children")

    print(f"\nData points checked: {checked}   Mismatches: {mismatches}")
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
