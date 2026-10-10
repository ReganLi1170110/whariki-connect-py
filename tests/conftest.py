"""Shared pytest fixtures for the Whāriki Connect test suite.

The repository functions talk to PostgreSQL through Flask's request-scoped
connection (app/db/db.py), so every database test runs inside
flask_app.test_request_context(). Popping that context runs the app's
teardown_request hook, which returns the connection to the pool.

Database tests never rely on the seeded demo data. The `fixture_data`
fixture creates its own users, children and classroom (all tagged with the
"pytest_" prefix / "__pytest_room__" classroom) at the start of the test
session and deletes them again at the end, so the suite can run against
the normal development database without changing it.

Run from the project root:
    python -m pytest -v
"""
import os
import sys
from datetime import date

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import flask_app  # noqa: E402
from app.utils import get_cursor, flask_bcrypt  # noqa: E402

TEST_ROOM = "__pytest_room__"
OTHER_ROOM = "__pytest_other_room__"
TEST_PASSWORD = "PytestPass!123"


@pytest.fixture(scope="session")
def app():
    flask_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    return flask_app


@pytest.fixture
def db(app):
    """A request context, so repository functions can open a connection."""
    with app.test_request_context():
        yield


def _sql(app, query, params=None, fetch=False):
    with app.test_request_context():
        with get_cursor() as cursor:
            cursor.execute(query, params or ())
            if fetch:
                return cursor.fetchall()
    return None


def _cleanup(app):
    _sql(app, "DELETE FROM Timesheet_Entries WHERE teacher_id IN "
              "(SELECT user_id FROM Users WHERE email LIKE 'pytest_%%');")
    _sql(app, "DELETE FROM Events WHERE created_by IN "
              "(SELECT user_id FROM Users WHERE email LIKE 'pytest_%%');")
    _sql(app, "DELETE FROM Notifications WHERE user_id IN "
              "(SELECT user_id FROM Users WHERE email LIKE 'pytest_%%');")
    # Children cascade to attendance, stories, accident forms, routines, links.
    _sql(app, "DELETE FROM Children WHERE classroom IN (%s, %s);", (TEST_ROOM, OTHER_ROOM))
    _sql(app, "DELETE FROM Users WHERE email LIKE 'pytest_%%';")


@pytest.fixture(scope="session")
def fixture_data(app):
    """Creates one teacher per test room, a parent, an admin, and three children."""
    _cleanup(app)  # in case a previous run was interrupted
    pw_hash = flask_bcrypt.generate_password_hash(TEST_PASSWORD).decode("utf-8")

    def add_user(role, name, email, classroom=None):
        rows = _sql(app,
                    """INSERT INTO Users (role, full_name, email, password_hash, classroom, status)
                       VALUES (%s, %s, %s, %s, %s, 'approved') RETURNING user_id;""",
                    (role, name, email, pw_hash, classroom), fetch=True)
        return rows[0]["user_id"]

    def add_child(first, classroom):
        rows = _sql(app,
                    """INSERT INTO Children (first_name, last_name, date_of_birth, classroom)
                       VALUES (%s, 'Pytest', %s, %s) RETURNING child_id;""",
                    (first, date(2022, 3, 1), classroom), fetch=True)
        return rows[0]["child_id"]

    data = {
        "teacher_id": add_user("Teacher", "Pytest Teacher", "pytest_teacher@example.test", TEST_ROOM),
        "other_teacher_id": add_user("Teacher", "Pytest Other", "pytest_other@example.test", OTHER_ROOM),
        "parent_id": add_user("Parent", "Pytest Parent", "pytest_parent@example.test"),
        "admin_id": add_user("Admin", "Pytest Admin", "pytest_admin@example.test"),
        "child_a": add_child("Alpha", TEST_ROOM),
        "child_b": add_child("Beta", TEST_ROOM),
        "child_other": add_child("Gamma", OTHER_ROOM),
    }
    # The parent is linked to child_a only.
    _sql(app, "INSERT INTO Parent_Child (parent_id, child_id) VALUES (%s, %s);",
         (data["parent_id"], data["child_a"]))

    data["teacher"] = {"user_id": data["teacher_id"], "role": "Teacher", "classroom": TEST_ROOM}
    data["other_teacher"] = {"user_id": data["other_teacher_id"], "role": "Teacher", "classroom": OTHER_ROOM}
    data["parent"] = {"user_id": data["parent_id"], "role": "Parent", "classroom": None}

    yield data
    _cleanup(app)


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, password=TEST_PASSWORD):
    return client.post("/login", data={"email": email, "password": password}, follow_redirects=False)
