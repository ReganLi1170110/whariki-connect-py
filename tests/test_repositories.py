"""Repository tests against a real PostgreSQL database.

These call the repository functions directly with known data created by the
`fixture_data` fixture, and check the results. Strictly speaking they are
integration tests (the database is real, not mocked), which is deliberate:
most of the logic that matters - role scoping, joins, aggregation - lives
in the SQL itself.
"""
from datetime import date, datetime, time, timedelta

import pytest

from app.repository import (
    attendance_repository, accident_repository, child_repository,
    events_repository, learning_story_repository, timesheet_repository,
    analytics_repository,
)
from app.utils import get_cursor

STRANDS = analytics_repository.STRAND_ORDER


def _accident(child_id, teacher_id, status, injury="Graze / scrape", day=date(2026, 9, 1)):
    return {
        "child_id": child_id, "teacher_id": teacher_id, "incident_date": day,
        "incident_time": time(10, 30), "location": "Sandpit", "nature_of_injury": injury,
        "body_part": "Knee", "description": "Tripped while running.",
        "action_taken": "Cleaned and applied a plaster.", "additional_information": None,
        "parent_contacted": False, "parent_contacted_name": None, "contacted_by": None,
        "contact_method": None, "contact_method_other": None, "parent_contacted_time": None,
        "other_actions_taken": None, "medical_attention_needed": False,
        "notifiable_event": False, "status": status, "provider_signature": "Pytest Teacher",
        "teacher_signed_at": datetime(2026, 9, 1, 11, 0),
    }


# ---------- Children: role scoping ----------

def test_teacher_only_sees_children_in_own_room(db, fixture_data):
    names = {c["first_name"] for c in child_repository.list_children_for_user(fixture_data["teacher"])}
    assert {"Alpha", "Beta"} <= names
    assert "Gamma" not in names


def test_parent_only_sees_own_child(db, fixture_data):
    children = child_repository.list_children_for_user(fixture_data["parent"])
    assert [c["first_name"] for c in children] == ["Alpha"]


def test_access_check_blocks_other_room_and_other_families(db, fixture_data):
    d = fixture_data
    assert child_repository.can_access_child(d["teacher"], d["child_a"])
    assert not child_repository.can_access_child(d["teacher"], d["child_other"])
    assert child_repository.can_access_child(d["parent"], d["child_a"])
    assert not child_repository.can_access_child(d["parent"], d["child_b"])


# ---------- Attendance ----------

def test_check_in_then_check_out(db, fixture_data):
    child = fixture_data["child_a"]
    day = date(2026, 9, 15)
    row = attendance_repository.check_in(child, fixture_data["teacher_id"], day)
    assert row["status"] == "present" and row["check_in_time"] is not None
    assert row["check_out_time"] is None

    row = attendance_repository.check_out(child, day)
    assert row["check_out_time"] is not None
    assert attendance_repository.get_attendance_for_date(child, day)["status"] == "present"


def test_teacher_correction_overwrites_the_day(db, fixture_data):
    child = fixture_data["child_b"]
    day = date(2026, 9, 16)
    attendance_repository.check_in(child, fixture_data["teacher_id"], day)
    attendance_repository.set_attendance(child, day, "sick", fixture_data["teacher_id"])
    assert attendance_repository.get_attendance_for_date(child, day)["status"] == "sick"


# ---------- Learning stories: draft vs published ----------

def test_parents_never_see_draft_stories(db, fixture_data):
    d = fixture_data
    published = learning_story_repository.create_story(
        d["child_a"], d["teacher_id"], "Pytest published", "Content", ["Wellbeing"], [],
        STRANDS, [], status="published")
    draft = learning_story_repository.create_story(
        d["child_a"], d["teacher_id"], "Pytest draft", "Content", ["Belonging"], [],
        STRANDS, [], status="draft")

    parent_ids = {s["story_id"] for s in learning_story_repository.list_stories_for_user(d["parent"])}
    teacher_ids = {s["story_id"] for s in learning_story_repository.list_stories_for_user(d["teacher"])}

    assert published in parent_ids and draft not in parent_ids
    assert {published, draft} <= teacher_ids


def test_unknown_strands_are_dropped(db, fixture_data):
    d = fixture_data
    story_id = learning_story_repository.create_story(
        d["child_b"], d["teacher_id"], "Pytest strands", "Content",
        ["Exploration", "NotAStrand"], [], STRANDS, [], status="draft")
    assert learning_story_repository.get_story(story_id)["strands"] == ["Exploration"]


# ---------- Accident forms ----------

def test_parent_sees_submitted_forms_only_and_can_acknowledge(db, fixture_data):
    d = fixture_data
    submitted = accident_repository.create_accident_form(_accident(d["child_a"], d["teacher_id"], "submitted"))
    draft = accident_repository.create_accident_form(_accident(d["child_a"], d["teacher_id"], "draft"))

    parent_view = {f["accident_id"] for f in accident_repository.list_for_user(d["parent"])}
    assert submitted in parent_view and draft not in parent_view

    assert accident_repository.acknowledge(submitted, d["parent_id"])
    assert accident_repository.get_accident(submitted)["parent_acknowledged_at"] is not None


def test_parent_cannot_acknowledge_another_familys_form(db, fixture_data):
    d = fixture_data
    form = accident_repository.create_accident_form(_accident(d["child_b"], d["teacher_id"], "submitted"))
    assert not accident_repository.acknowledge(form, d["parent_id"])
    assert accident_repository.get_accident(form)["parent_acknowledged_at"] is None


# ---------- Events: classroom visibility ----------

def test_room_events_are_hidden_from_other_rooms(db, fixture_data):
    d = fixture_data
    room_event = events_repository.create_event(
        d["teacher_id"], "__pytest_room__", "Pytest room trip", None, "excursion", date(2099, 1, 10))
    centre_event = events_repository.create_event(
        d["teacher_id"], events_repository.ALL_CLASSROOMS_LABEL, "Pytest centre day", None,
        "photo_day", date(2099, 1, 11))

    other_view = {e["event_id"] for e in events_repository.list_upcoming(d["other_teacher"], limit=500)}
    parent_view = {e["event_id"] for e in events_repository.list_upcoming(d["parent"], limit=500)}

    assert centre_event in other_view and room_event not in other_view
    assert {room_event, centre_event} <= parent_view  # parent's child is in the room


# ---------- Timesheet ----------

def test_week_has_seven_rows_and_approval_locks_entries(db, fixture_data):
    d = fixture_data
    monday = date(2026, 9, 21)
    timesheet_repository.upsert_entry(d["teacher_id"], monday + timedelta(days=2),
                                      time(8, 0), time(16, 30), 30, "pytest", d["teacher_id"])
    rows = timesheet_repository.list_week_for_teacher(d["teacher_id"], monday)

    assert len(rows) == 7
    assert [r["entry"] is not None for r in rows] == [False, False, True, False, False, False, False]
    assert timesheet_repository.hours_worked(rows[2]["entry"]) == 8.0

    timesheet_repository.approve_week(d["teacher_id"], monday, d["teacher_id"])
    assert timesheet_repository.get_entry(d["teacher_id"], monday + timedelta(days=2))["status"] == "approved"


# ---------- Analytics queries vs hand-calculated values ----------

def test_strand_coverage_counts_match_known_data(db, fixture_data):
    d = fixture_data
    with get_cursor() as cursor:  # start from a clean slate for this room
        cursor.execute("DELETE FROM Learning_Stories WHERE child_id = %s;", (d["child_other"],))
    for strands in (["Wellbeing", "Belonging"], ["Wellbeing"], ["Exploration"]):
        learning_story_repository.create_story(
            d["child_other"], d["other_teacher_id"], "Pytest", "x", strands, [], STRANDS, [])

    result = analytics_repository.strand_coverage(classroom="__pytest_other_room__")
    # Hand count: Wellbeing 2, Belonging 1, Contribution 0, Communication 0, Exploration 1
    assert result == [
        {"strand": "Wellbeing", "count": 2}, {"strand": "Belonging", "count": 1},
        {"strand": "Contribution", "count": 0}, {"strand": "Communication", "count": 0},
        {"strand": "Exploration", "count": 1},
    ]


def test_attendance_rate_matches_hand_calculation(db, fixture_data):
    d = fixture_data
    child = d["child_other"]
    week = date(2026, 8, 3)  # a Monday
    with get_cursor() as cursor:
        cursor.execute("DELETE FROM Attendance WHERE child_id = %s;", (child,))
    # Mon-Thu present, Fri absent -> 4 / 5 = 80.0 %
    for i, status in enumerate(["present", "present", "present", "present", "absent"]):
        attendance_repository.set_attendance(child, week + timedelta(days=i), status, d["other_teacher_id"])

    rows = analytics_repository.attendance_trend(classroom="__pytest_other_room__")
    assert len(rows) == 1
    assert rows[0]["week_start"] == week
    assert float(rows[0]["present_pct"]) == 80.0


def test_accident_frequency_counts_submitted_forms_only(db, fixture_data):
    d = fixture_data
    child = d["child_other"]
    with get_cursor() as cursor:
        cursor.execute("DELETE FROM Accident_Forms WHERE child_id = %s;", (child,))
    for injury, status in [("Bruise", "submitted"), ("Bruise", "submitted"),
                           ("Bite", "submitted"), ("Bite", "draft")]:
        accident_repository.create_accident_form(_accident(child, d["other_teacher_id"], status, injury))

    rows = analytics_repository.accident_frequency(classroom="__pytest_other_room__")
    assert [(r["nature"], r["count"]) for r in rows] == [("Bruise", 2), ("Bite", 1)]


# ---------- Documentation gaps (UAT request: who has no recent story?) ----------

def test_documentation_gaps_lists_children_without_recent_stories(db, fixture_data):
    d = fixture_data
    with get_cursor() as cursor:
        cursor.execute("DELETE FROM Learning_Stories WHERE child_id IN (%s, %s);", (d["child_a"], d["child_b"]))
    # child_a gets a story today; child_b only an old one (10 weeks ago)
    learning_story_repository.create_story(d["child_a"], d["teacher_id"], "Recent", "x", [], [], STRANDS, [])
    old_id = learning_story_repository.create_story(d["child_b"], d["teacher_id"], "Old", "x", [], [], STRANDS, [])
    with get_cursor() as cursor:
        cursor.execute("UPDATE Learning_Stories SET created_at = now() - interval '10 weeks' WHERE story_id = %s;", (old_id,))

    gaps, total = analytics_repository.documentation_gaps("__pytest_room__", weeks=4)
    names = [g["first_name"] for g in gaps]
    assert total == 2
    assert names == ["Beta"]
    assert gaps[0]["last_story_at"] is not None

    gaps, _ = analytics_repository.documentation_gaps("__pytest_room__", weeks=12)
    assert gaps == []
