# Analytics Routes
# Teacher/Admin dashboard (Sub-goal 3): R/ggplot2 charts generated from the
# app's own data. Each chart is its own collapsible section with an
# independent date-range filter, so filtering one chart doesn't disturb the
# others and a slow/irrelevant chart can stay collapsed. Every chart can
# also be downloaded as a PNG straight from its section.

from datetime import datetime

from flask import render_template, request, session, Response
from app import flask_app as app
import app.utils as utils
from app.repository import analytics_repository, child_repository
from app import r_runner


def _current_user():
    return {
        "user_id": session["user_id"],
        "role": session["role"],
        "classroom": session.get("classroom"),
    }


def _parse_date(raw):
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None


def _classroom_for(user):
    # Admin sees the whole centre; a teacher sees their own room only - same
    # scoping rule already used for Events and Announcements.
    return None if user["role"] == "Admin" else user["classroom"]


@app.route("/analytics", methods=["GET"])
@utils.login_required()
@utils.roles_required("Teacher", "Admin")
def analytics():
    user = _current_user()
    classroom = _classroom_for(user)

    filters = {}
    for section in ("strand", "attendance", "accident", "routine"):
        start_raw = request.args.get(f"{section}_start", "")
        end_raw = request.args.get(f"{section}_end", "")
        filters[section] = {
            "start_raw": start_raw,
            "end_raw": end_raw,
            "start": _parse_date(start_raw),
            "end": _parse_date(end_raw),
            # Keep a section's accordion open after it's been filtered, so
            # adjusting the range doesn't feel like it closes on you.
            "is_open": bool(start_raw or end_raw),
        }

    # The routine chart is inherently per-child - a classroom-wide "average
    # routine" wouldn't mean much - so it needs its own child picker rather
    # than the classroom/centre scoping the other three charts use.
    routine_child_id = request.args.get("routine_child_id", type=int)
    routine_children = child_repository.list_children_for_user(user)
    if routine_child_id and not child_repository.can_access_child(user, routine_child_id):
        routine_child_id = None
    filters["routine"]["is_open"] = filters["routine"]["is_open"] or bool(routine_child_id)

    strand_rows = analytics_repository.strand_coverage(
        classroom, filters["strand"]["start"], filters["strand"]["end"])
    attendance_rows = analytics_repository.attendance_trend(
        classroom, filters["attendance"]["start"], filters["attendance"]["end"])
    accident_rows = analytics_repository.accident_frequency(
        classroom, filters["accident"]["start"], filters["accident"]["end"])

    gap_weeks = request.args.get("gap_weeks", type=int)
    if gap_weeks not in (2, 4, 6, 8):
        gap_weeks = 4
    gap_rows, gap_total = analytics_repository.documentation_gaps(classroom, gap_weeks)

    routine_rows = []
    if routine_child_id:
        routine_rows = analytics_repository.routine_trend(
            routine_child_id, filters["routine"]["start"], filters["routine"]["end"])

    return render_template(
        "analytics.html",
        classroom_label=classroom or "the whole centre",
        filters=filters,
        strand_empty=not any(r["count"] for r in strand_rows),
        attendance_empty=not attendance_rows,
        accident_empty=not accident_rows,
        routine_children=routine_children,
        routine_child_id=routine_child_id,
        routine_empty=not routine_rows,
        gap_rows=gap_rows,
        gap_total=gap_total,
        gap_weeks=gap_weeks,
        today=datetime.now(),
    )


def _chart_query_string():
    """Builds the ?start=...&end=... a chart endpoint expects, from whichever
    section's params are on the current request - keeps the PNG endpoints
    generic instead of one per section name."""
    start = request.args.get("start", "")
    end = request.args.get("end", "")
    return _parse_date(start), _parse_date(end)


def _render_or_error(script_name, rows, fieldnames, title, download_name=None):
    try:
        png_bytes = r_runner.run_chart_script(
            script_name, rows, fieldnames=fieldnames,
            output_name="chart.png", title=title,
        )
    except (r_runner.RNotConfigured, r_runner.RScriptError) as exc:
        app.logger.warning("%s chart failed: %s", script_name, exc.message)
        return Response(exc.message, status=503, mimetype="text/plain")

    headers = {}
    # ?download=1 forces a save-as instead of the browser just displaying it
    # inline - the same endpoint serves both the on-page <img> and the
    # "Download" link, so the chart is never generated twice.
    if request.args.get("download") and download_name:
        headers["Content-Disposition"] = f"attachment; filename={download_name}"
    return Response(png_bytes, mimetype="image/png", headers=headers)


@app.route("/analytics/chart/strand-coverage.png", methods=["GET"])
@utils.login_required()
@utils.roles_required("Teacher", "Admin")
def strand_coverage_chart():
    user = _current_user()
    classroom = _classroom_for(user)
    start, end = _chart_query_string()
    rows = analytics_repository.strand_coverage(classroom, start, end)
    title = f"Learning stories per Te Wh\u0101riki strand \u2014 {classroom or 'whole centre'}"
    return _render_or_error("strand_coverage.R", rows, ["strand", "count"], title,
                            download_name="strand_coverage.png")


@app.route("/analytics/chart/attendance-trend.png", methods=["GET"])
@utils.login_required()
@utils.roles_required("Teacher", "Admin")
def attendance_trend_chart():
    user = _current_user()
    classroom = _classroom_for(user)
    start, end = _chart_query_string()
    rows = analytics_repository.attendance_trend(classroom, start, end)
    title = f"Weekly attendance rate \u2014 {classroom or 'whole centre'}"
    return _render_or_error("attendance_trend.R", rows, ["week_start", "present_pct"], title,
                            download_name="attendance_trend.png")


@app.route("/analytics/chart/accident-frequency.png", methods=["GET"])
@utils.login_required()
@utils.roles_required("Teacher", "Admin")
def accident_frequency_chart():
    user = _current_user()
    classroom = _classroom_for(user)
    start, end = _chart_query_string()
    rows = analytics_repository.accident_frequency(classroom, start, end)
    title = f"Accident frequency by injury type \u2014 {classroom or 'whole centre'}"
    return _render_or_error("accident_frequency.R", rows, ["nature", "count"], title,
                            download_name="accident_frequency.png")


@app.route("/analytics/chart/routine-trend.png", methods=["GET"])
@utils.login_required()
def routine_trend_chart():
    # No roles_required here on purpose: can_access_child below already
    # scopes this correctly per role (Parent to their own child, Teacher to
    # their own room, Admin to everyone) - the same check every other
    # per-child page in the app uses, so a Parent can see their own child's
    # chart without also being able to reach /analytics itself, which shows
    # classroom/centre-wide data that isn't theirs to see.
    user = _current_user()
    child_id = request.args.get("child_id", type=int)

    if not child_id or not child_repository.can_access_child(user, child_id):
        return Response("Select a child to see their routine trend.", status=400, mimetype="text/plain")

    child = child_repository.get_child_by_id(child_id)
    start, end = _chart_query_string()
    rows = analytics_repository.routine_trend(child_id, start, end)
    title = f"Weekly routine trends \u2014 {child['first_name']} {child['last_name']}"
    safe_name = f"routine_trend_{child['first_name']}_{child['last_name']}.png".replace(" ", "_")
    return _render_or_error(
        "routine_trend.R", rows, ["week_start", "meal_score", "toileting_issue_pct"], title,
        download_name=safe_name,
    )
