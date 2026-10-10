# Timesheet Routes
# Actual hours worked, filled in and edited by the teacher themselves. An
# admin can view and correct any teacher's timesheet, and approve a week
# (e.g. once payroll has been run) which locks it against further teacher
# edits - only an admin can change an approved entry after that.

from datetime import datetime, date, timedelta

from flask import render_template, request, redirect, url_for, flash, session
from app import flask_app as app
import app.utils as utils
from app.repository import timesheet_repository, user_repository

DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


def _parse_week_start(raw):
    if raw:
        try:
            return timesheet_repository.week_start_for(datetime.strptime(raw, "%Y-%m-%d").date())
        except ValueError:
            pass
    return timesheet_repository.week_start_for(date.today())


def _week_total(week_rows):
    return round(sum(timesheet_repository.hours_worked(r['entry']) for r in week_rows if r['entry']), 2)


def _save_week_from_form(teacher_id, week_start, form, edited_by, allow_locked=False):
    """Shared by the teacher's own save and the admin's save. Returns the
    number of days actually written, and a list of (date, reason) skipped
    because they were locked and allow_locked was False."""
    saved, skipped = 0, []

    for i in range(7):
        work_date = week_start + timedelta(days=i)
        prefix = f"day_{i}"
        start_raw = form.get(f"{prefix}_start", "").strip()
        end_raw = form.get(f"{prefix}_end", "").strip()

        if not start_raw or not end_raw:
            continue  # blank row - no shift recorded that day, nothing to save

        existing = timesheet_repository.get_entry(teacher_id, work_date)
        if existing and existing['status'] == 'approved' and not allow_locked:
            skipped.append(work_date)
            continue

        try:
            start_time = datetime.strptime(start_raw, "%H:%M").time()
            end_time = datetime.strptime(end_raw, "%H:%M").time()
        except ValueError:
            skipped.append(work_date)
            continue

        break_minutes = form.get(f"{prefix}_break", type=int) or 0
        notes = form.get(f"{prefix}_notes", "").strip() or None

        timesheet_repository.upsert_entry(
            teacher_id, work_date, start_time, end_time, break_minutes, notes, edited_by
        )
        saved += 1

    return saved, skipped


@app.route("/timesheet", methods=["GET"])
@utils.login_required()
@utils.roles_required("Teacher")
def timesheet():
    week_start = _parse_week_start(request.args.get("week_start", ""))
    rows = timesheet_repository.list_week_for_teacher(session["user_id"], week_start)

    return render_template(
        "timesheet.html",
        rows=rows, day_names=DAY_NAMES,
        week_start=week_start, week_end=week_start + timedelta(days=6),
        prev_week=week_start - timedelta(days=7), next_week=week_start + timedelta(days=7),
        week_total=_week_total(rows),
        is_admin_view=False,
    )


@app.route("/timesheet/save", methods=["POST"])
@utils.login_required()
@utils.roles_required("Teacher")
def save_timesheet():
    week_start = _parse_week_start(request.form.get("week_start", ""))
    saved, skipped = _save_week_from_form(
        session["user_id"], week_start, request.form, session["user_id"], allow_locked=False
    )

    if skipped:
        flash(f"{len(skipped)} day(s) weren't updated because an admin has already "
              f"approved them for payroll. Contact your admin if one of those needs correcting.", "danger")
    if saved:
        flash(f"Saved {saved} day(s) for the week of {week_start.strftime('%d %b %Y')}.", "success")
    elif not skipped:
        flash("No hours entered - nothing to save.", "danger")

    return redirect(url_for("timesheet", week_start=week_start.isoformat()))


@app.route("/timesheet/admin", methods=["GET"])
@utils.login_required()
@utils.roles_required("Admin")
def admin_timesheet():
    teachers = timesheet_repository.list_teachers()
    teacher_id = request.args.get("teacher_id", type=int) or (teachers[0]["user_id"] if teachers else None)
    week_start = _parse_week_start(request.args.get("week_start", ""))

    rows = []
    if teacher_id:
        rows = timesheet_repository.list_week_for_teacher(teacher_id, week_start)

    return render_template(
        "timesheet_admin.html",
        teachers=teachers, active_teacher_id=teacher_id,
        rows=rows, day_names=DAY_NAMES,
        week_start=week_start, week_end=week_start + timedelta(days=6),
        prev_week=week_start - timedelta(days=7), next_week=week_start + timedelta(days=7),
        week_total=_week_total(rows),
        month_totals=timesheet_repository.monthly_totals_for_all_teachers(date.today().year, date.today().month),
    )


@app.route("/timesheet/admin/save", methods=["POST"])
@utils.login_required()
@utils.roles_required("Admin")
def admin_save_timesheet():
    teacher_id = request.form.get("teacher_id", type=int)
    week_start = _parse_week_start(request.form.get("week_start", ""))

    if not teacher_id or not user_repository.get_user_by_id(teacher_id):
        flash("Please choose a valid teacher.", "danger")
        return redirect(url_for("admin_timesheet"))

    # Admins can always write, even to an already-approved day.
    saved, _ = _save_week_from_form(teacher_id, week_start, request.form, session["user_id"], allow_locked=True)
    flash(f"Saved {saved} day(s).", "success")
    return redirect(url_for("admin_timesheet", teacher_id=teacher_id, week_start=week_start.isoformat()))


@app.route("/timesheet/admin/approve", methods=["POST"])
@utils.login_required()
@utils.roles_required("Admin")
def approve_timesheet_week():
    teacher_id = request.form.get("teacher_id", type=int)
    week_start = _parse_week_start(request.form.get("week_start", ""))
    timesheet_repository.approve_week(teacher_id, week_start, session["user_id"])
    flash("Week approved and locked for payroll.", "success")
    return redirect(url_for("admin_timesheet", teacher_id=teacher_id, week_start=week_start.isoformat()))


@app.route("/timesheet/admin/unapprove", methods=["POST"])
@utils.login_required()
@utils.roles_required("Admin")
def unapprove_timesheet_week():
    teacher_id = request.form.get("teacher_id", type=int)
    week_start = _parse_week_start(request.form.get("week_start", ""))
    timesheet_repository.unapprove_week(teacher_id, week_start, session["user_id"])
    flash("Week reopened for editing.", "success")
    return redirect(url_for("admin_timesheet", teacher_id=teacher_id, week_start=week_start.isoformat()))
