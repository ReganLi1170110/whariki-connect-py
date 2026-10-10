"""Functional tests through Flask's test client: login, role-based access,
and the signup password rules - what a user actually experiences."""
from tests.conftest import TEST_PASSWORD, login


def test_wrong_password_is_rejected(client, fixture_data):
    response = client.post("/login", data={"email": "pytest_teacher@example.test",
                                           "password": "WrongPass!999"})
    assert b"Invalid email or password" in response.data
    assert client.get("/overview").status_code == 302  # still not logged in


def test_pages_require_login(client):
    for path in ["/overview", "/children", "/attendance", "/learning-stories", "/analytics"]:
        response = client.get(path)
        assert response.status_code == 302 and "/login" in response.headers["Location"]


def test_teacher_can_open_core_pages(client, fixture_data):
    assert login(client, "pytest_teacher@example.test").status_code == 302
    for path in ["/overview", "/children", "/attendance", "/learning-stories",
                 "/accidents", "/events", "/messages", "/library", "/analytics", "/timesheet"]:
        assert client.get(path).status_code == 200, path


def test_parent_is_kept_out_of_analytics_and_timesheets(client, fixture_data):
    login(client, "pytest_parent@example.test")
    assert client.get("/overview").status_code == 200
    for path in ["/analytics", "/timesheet", "/learning-stories/new"]:
        response = client.get(path)
        assert response.status_code == 302 and "/overview" in response.headers["Location"], path


def test_parent_cannot_open_another_familys_child(client, fixture_data):
    login(client, "pytest_parent@example.test")
    assert client.get(f"/children/{fixture_data['child_a']}").status_code == 200
    response = client.get(f"/children/{fixture_data['child_b']}")
    assert response.status_code != 200


def test_signup_rejects_mismatched_and_weak_passwords(client):
    base = {"full_name": "Pytest Signup", "email": "pytest_signup@example.test",
            "role": "Parent", "phone": "", "classroom": ""}
    weak = client.post("/signup", data={**base, "password": "short", "confirm_password": "short"})
    assert b"more than 8 characters" in weak.data

    mismatch = client.post("/signup", data={**base, "password": "Kowhai!2026",
                                            "confirm_password": "Kowhai!2027"})
    assert b"match" in mismatch.data


def test_admin_staff_table_shows_account_status(client, fixture_data):
    # Regression: the Staff & families table used to render an empty status
    # pill for every account because the query did not select `status`.
    login(client, "pytest_admin@example.test")
    html = client.get("/admin").get_data(as_text=True)
    assert 'status-present">approved</span>' in html


def test_admin_staff_table_search_and_filters(client, fixture_data):
    # UAT feedback: finding one person meant scrolling the whole table.
    login(client, "pytest_admin@example.test")
    html = client.get("/admin?q=pytest_parent").get_data(as_text=True)
    assert "pytest_parent@example.test" in html
    assert "pytest_teacher@example.test" not in html

    html = client.get("/admin?q=pytest&role=Teacher").get_data(as_text=True)
    assert "pytest_teacher@example.test" in html
    assert "pytest_parent@example.test" not in html

    html = client.get("/admin?q=nobody-matches-this").get_data(as_text=True)
    assert "No accounts match these filters." in html


def test_ai_assistant_only_receives_first_name(client, fixture_data, monkeypatch):
    # UAT feedback (privacy): only the child's first name may leave the app.
    from app import ai_assistant
    seen = {}

    def fake_ask(child_name, draft, history):
        seen["child_name"] = child_name
        return "ok"

    monkeypatch.setattr(ai_assistant, "ask", fake_ask)
    login(client, "pytest_teacher@example.test")
    response = client.post("/learning-stories/ai-assist", json={
        "child_name": "Alpha Pytest", "draft": "", "history": [{"role": "user", "content": "hi"}]})
    assert response.status_code == 200
    assert seen["child_name"] == "Alpha"


def test_analytics_shows_documentation_gaps(client, fixture_data):
    login(client, "pytest_teacher@example.test")
    html = client.get("/analytics?gap_weeks=2").get_data(as_text=True)
    assert "Documentation gaps" in html
