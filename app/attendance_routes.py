# Attendance Routes
# Attendance has its own page: parents check their own child in and out,
# teachers get a month calendar they can correct any day from.

import calendar as pycalendar
import csv
import io
from datetime import date, datetime

from flask import render_template, request, redirect, url_for, flash, session, Response
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


@app.route("/attendance/history", methods=["GET"])
@utils.login_required()
def attendance_history():
    """Searchable log across every child the user can access - the today
    snapshot page only ever shows today, so this is where you'd look up
    "was child X absent last Tuesday" as records pile up."""
    user = _current_user()
    children = child_repository.list_children_for_user(user)
    child_ids = [c["child_id"] for c in children]

    child_id = request.args.get("child_id", type=int)
    status = request.args.get("status", "").strip() or None

    def _parse_date(name):
        raw = request.args.get(name, "").strip()
        if not raw:
            return None
        try:
            return datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            return None

    start_date = _parse_date("start_date")
    end_date = _parse_date("end_date")

    if child_id and not child_repository.can_access_child(user, child_id):
        flash("You do not have access to that child's records.", "danger")
        return redirect(url_for("attendance_history"))

    scoped_ids = [child_id] if child_id else child_ids

    return render_template(
        "attendance_history.html",
        children=children,
        rows=attendance_repository.list_history_for_children(scoped_ids, start_date, end_date, status),
        active_child_id=child_id,
        active_status=status or "",
        active_start_date=request.args.get("start_date", ""),
        active_end_date=request.args.get("end_date", ""),
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


STATUS_LABELS = {
    "present": "Present", "absent": "Absent", "sick": "Sick", "on_leave": "On leave",
}


def _export_month_args():
    today = date.today()
    year = request.args.get("year", type=int) or today.year
    month = request.args.get("month", type=int) or today.month
    if not 1 <= month <= 12:
        year, month = today.year, today.month
    return year, month


@app.route("/attendance/<int:child_id>/export.csv", methods=["GET"])
@utils.login_required()
def attendance_export_csv(child_id):
    user = _current_user()
    if not child_repository.can_access_child(user, child_id):
        flash("You do not have access to that child's records.", "danger")
        return redirect(url_for("attendance"))

    child = child_repository.get_child_by_id(child_id)
    year, month = _export_month_args()
    rows = attendance_repository.list_attendance_rows_for_month(child_id, year, month)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([f"{child['first_name']} {child['last_name']} — attendance for "
                      f"{pycalendar.month_name[month]} {year}"])
    writer.writerow([])
    writer.writerow(["Date", "Day", "Status", "Check-in", "Check-out"])
    for r in rows:
        writer.writerow([
            r["date"].strftime("%Y-%m-%d"),
            r["date"].strftime("%A"),
            STATUS_LABELS.get(r["status"], r["status"]),
            r["check_in_time"].strftime("%I:%M %p") if r["check_in_time"] else "",
            r["check_out_time"].strftime("%I:%M %p") if r["check_out_time"] else "",
        ])

    present_days = sum(1 for r in rows if r["status"] == "present")
    writer.writerow([])
    writer.writerow([f"Days present: {present_days} of {len(rows)} recorded days"])

    filename = f"{child['first_name']}_{child['last_name']}_attendance_{year}-{month:02d}.csv"
    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.route("/attendance/<int:child_id>/export.pdf", methods=["GET"])
@utils.login_required()
def attendance_export_pdf(child_id):
    user = _current_user()
    if not child_repository.can_access_child(user, child_id):
        flash("You do not have access to that child's records.", "danger")
        return redirect(url_for("attendance"))

    child = child_repository.get_child_by_id(child_id)
    year, month = _export_month_args()
    rows = attendance_repository.list_attendance_rows_for_month(child_id, year, month)

    # Imported here rather than at module load so the rest of the app still
    # runs even in an environment where reportlab hasn't been installed yet.
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()

    story = [
        Paragraph(f"{child['first_name']} {child['last_name']} — Attendance", styles["Title"]),
        Paragraph(f"{pycalendar.month_name[month]} {year} · {child['classroom']}", styles["Normal"]),
        Spacer(1, 10 * mm),
    ]

    table_data = [["Date", "Day", "Status", "Check-in", "Check-out"]]
    for r in rows:
        table_data.append([
            r["date"].strftime("%d %b %Y"),
            r["date"].strftime("%A"),
            STATUS_LABELS.get(r["status"], r["status"]),
            r["check_in_time"].strftime("%I:%M %p") if r["check_in_time"] else "—",
            r["check_out_time"].strftime("%I:%M %p") if r["check_out_time"] else "—",
        ])

    table = Table(table_data, colWidths=[28 * mm, 28 * mm, 25 * mm, 28 * mm, 28 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3B2C")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F1EA")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D8D3C4")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)

    present_days = sum(1 for r in rows if r["status"] == "present")
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(f"Days present: {present_days} of {len(rows)} recorded days", styles["Normal"]))

    doc.build(story)
    buffer.seek(0)

    filename = f"{child['first_name']}_{child['last_name']}_attendance_{year}-{month:02d}.pdf"
    return Response(
        buffer.getvalue(),
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
