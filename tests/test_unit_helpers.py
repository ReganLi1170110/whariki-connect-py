"""Unit tests for pure helper functions - no database or Flask request needed.

Each test feeds a known input and checks the result against a value worked
out by hand beforehand.
"""
from datetime import date, time

import pytest

from app import utils
from app import r_runner
from app.repository import timesheet_repository


# ---------- Password policy (signup + password reset share this one rule) ----------

@pytest.mark.parametrize("password", [
    "Short!1A",          # 8 characters - the rule is MORE than 8
    "nouppercase!123",   # no capital letter
    "NoSpecialChar123",  # no special character
    "",                  # empty
])
def test_weak_passwords_are_rejected(password):
    assert utils.validate_password_strength(password) is not None


@pytest.mark.parametrize("password", [
    "Kowhai!2026",
    "Ab#defghi",         # exactly 9 characters - the shortest allowed
])
def test_strong_passwords_are_accepted(password):
    assert utils.validate_password_strength(password) is None


def test_password_error_message_names_the_missing_rule():
    assert "uppercase" in utils.validate_password_strength("lowercase!only1")
    assert "special" in utils.validate_password_strength("NoSpecials12345")


# ---------- Timesheet hours ----------

def _entry(start, end, break_minutes):
    return {"work_date": date(2026, 9, 21), "start_time": start,
            "end_time": end, "break_minutes": break_minutes}


def test_hours_worked_full_day_with_lunch_break():
    # 08:00-16:30 = 8.5 h, minus 30 min break = 8.0 h
    assert timesheet_repository.hours_worked(_entry(time(8, 0), time(16, 30), 30)) == 8.0


def test_hours_worked_rounds_to_two_decimals():
    # 09:00-12:20 = 200 min = 3.333... h
    assert timesheet_repository.hours_worked(_entry(time(9, 0), time(12, 20), 0)) == 3.33


def test_hours_worked_never_negative():
    # A break longer than the shift must not produce negative pay hours.
    assert timesheet_repository.hours_worked(_entry(time(9, 0), time(9, 30), 45)) == 0


@pytest.mark.parametrize("given, expected_monday", [
    (date(2026, 9, 23), date(2026, 9, 21)),  # Wednesday
    (date(2026, 9, 21), date(2026, 9, 21)),  # Monday is its own week start
    (date(2026, 9, 27), date(2026, 9, 21)),  # Sunday belongs to the week before
])
def test_week_start_is_the_monday(given, expected_monday):
    assert timesheet_repository.week_start_for(given) == expected_monday


# ---------- R detection ----------

def test_bad_rscript_override_gives_clear_message(monkeypatch):
    monkeypatch.setenv("RSCRIPT_PATH", "/definitely/not/here/Rscript")
    with pytest.raises(r_runner.RNotConfigured) as err:
        r_runner.find_rscript()
    assert "RSCRIPT_PATH" in err.value.message
