# Attendance Routes
# Attendance has its own page: parents check their own child in and out,
# teachers get a month calendar they can correct any day from.

import calendar as pycalendar
from datetime import date, datetime

from flask import render_template, request, redirect, url_for, flash, session
from app import flask_app as app
import app.utils as utils
from app.repository import child_repository, attendance_repository


def _current_user():
    return {
        "user_id": session["user_id"],
        "role": session["role"],
        "classroom": session.get("classroom"),
    }


@app.route("/attendance", methods=["GET"])
@utils.login_required()
def attendance():
    user = _current_user()
    children = child_repository.list_children_for_user(user)
    child_ids = [c["child_id"] for c in children]

    return render_template(
        "attendance.html",
        children=children,
        today_rows=attendance_repository.today_summary_for_children(child_ids),
        today=date.today(),
    )


@app.route("/attendance/<int:child_id>/calendar", methods=["GET"])
@utils.login_required()
def attendance_calendar(child_id):
    """Month view for one child. Teachers and admins can edit any day here."""
    user = _current_user()
    if not child_repository.can_access_child(user, child_id):
        flash("You do not have access to that child's records.", "danger")
        return redirect(url_for("attendance"))

    today = date.today()
    year = request.args.get("year", type=int) or today.year
    month = request.args.get("month", type=int) or today.month
    # Keep the month in range if someone hand-edits the query string.
    if not 1 <= month <= 12:
        year, month = today.year, today.month

    rows = attendance_repository.list_attendance_for_month(child_id, year, month)

    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)

    return render_template(
        "attendance_calendar.html",
        child=child_repository.get_child_by_id(child_id),
        weeks=pycalendar.Calendar(firstweekday=0).monthdayscalendar(year, month),
        rows=rows,
        year=year, month=month,
        month_name=pycalendar.month_name[month],
        today=today,
        prev_year=prev_year, prev_month=prev_month,
        next_year=next_year, next_month=next_month,
        can_edit=user["role"] in ("Teacher", "Admin"),
    )


@app.route("/attendance/<int:child_id>/checkin", methods=["POST"])
@utils.login_required()
def attendance_checkin(child_id):
    user = _current_user()
    if not child_repository.can_access_child(user, child_id):
        flash("You do not have access to that child's records.", "danger")
        return redirect(url_for("attendance"))

    attendance_repository.check_in(child_id, recorded_by=user["user_id"])
    flash("Checked in for today.", "success")
    return redirect(request.referrer or url_for("attendance"))


@app.route("/attendance/<int:child_id>/checkout", methods=["POST"])
@utils.login_required()
def attendance_checkout(child_id):
    user = _current_user()
    if not child_repository.can_access_child(user, child_id):
        flash("You do not have access to that child's records.", "danger")
        return redirect(url_for("attendance"))

    if not attendance_repository.check_out(child_id):
        flash("No check-in recorded for today yet.", "danger")
    else:
        flash("Checked out for today.", "success")
    return redirect(request.referrer or url_for("attendance"))


@app.route("/attendance/<int:child_id>/set", methods=["POST"])
@utils.login_required()
@utils.roles_required("Teacher", "Admin")
def attendance_set(child_id):
    """Teacher edits one day from the calendar, including past dates."""
    user = _current_user()
    if not child_repository.can_access_child(user, child_id):
        flash("This child is not in your classroom.", "danger")
        return redirect(url_for("attendance"))

    raw_date = request.form.get("date", "")
    status = request.form.get("status", "")
    check_in_raw = request.form.get("check_in_time", "").strip()
    check_out_raw = request.form.get("check_out_time", "").strip()

    if status not in ("present", "absent", "sick", "on_leave"):
        flash("Please choose a valid attendance status.", "danger")
        return redirect(url_for("attendance_calendar", child_id=child_id))

    try:
        target_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid date.", "danger")
        return redirect(url_for("attendance_calendar", child_id=child_id))

    def _combine(time_raw):
        if not time_raw:
            return None
        try:
            t = datetime.strptime(time_raw, "%H:%M").time()
        except ValueError:
            return None
        return datetime.combine(target_date, t)

    attendance_repository.set_attendance(
        child_id=child_id,
        date=target_date,
        status=status,
        recorded_by=user["user_id"],
        check_in_time=_combine(check_in_raw),
        check_out_time=_combine(check_out_raw),
    )

    flash(f"Attendance updated for {target_date.strftime('%d %b %Y')}.", "success")
    return redirect(url_for("attendance_calendar", child_id=child_id,
                            year=target_date.year, month=target_date.month))
