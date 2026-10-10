"""Server response times for the main pages and the R chart endpoints.

Logs in as a seeded Teacher, Parent and Admin through Flask's test client and
times each page RUNS times. Reports median and 95th percentile in
milliseconds. The test client calls the app in-process, so the numbers are
server-side time (routing, SQL, template rendering, R) without network
latency.

Usage (from the project root, against the seeded database):
    python evaluation/measure_response_times.py
"""
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import flask_app  # noqa: E402

RUNS = 20
SEED_PASSWORD = "Sunnypreschool123"  # shared password from generate_data.py

PAGES = {
    ("Teacher", "priya.patel@sunnypreschool.nz"): [
        "/overview", "/children", "/attendance", "/learning-stories", "/accidents",
        "/events", "/messages", "/library", "/timesheet", "/analytics",
        "/analytics/chart/strand-coverage.png", "/analytics/chart/attendance-trend.png",
        "/analytics/chart/accident-frequency.png",
    ],
    ("Parent", "liam.brown1@example.co.nz"): [
        "/overview", "/children", "/learning-stories", "/accidents", "/events",
    ],
    ("Admin", None): [
        "/overview", "/children", "/admin", "/analytics",
    ],
}


def admin_email():
    from app.utils import get_cursor
    with flask_app.test_request_context():
        with get_cursor() as cursor:
            cursor.execute("SELECT email FROM Users WHERE role = 'Admin' ORDER BY user_id LIMIT 1;")
            return cursor.fetchone()["email"]


def p95(values):
    ordered = sorted(values)
    return ordered[max(0, int(round(0.95 * len(ordered))) - 1)]


def main():
    flask_app.config["TESTING"] = True
    print(f"{'Role':<8} {'Page':<42} {'Median ms':>10} {'p95 ms':>8}")
    all_page_medians = []
    for (role, email), paths in PAGES.items():
        client = flask_app.test_client()
        email = email or admin_email()
        login = client.post("/login", data={"email": email, "password": SEED_PASSWORD})
        if login.status_code != 302:
            print(f"Could not log in as {role} ({email})")
            continue
        for path in paths:
            timings = []
            for _ in range(RUNS):
                started = time.perf_counter()
                response = client.get(path)
                timings.append((time.perf_counter() - started) * 1000)
                if response.status_code != 200:
                    print(f"  {path} returned {response.status_code}")
                    break
            median = statistics.median(timings)
            if not path.endswith(".png"):
                all_page_medians.append(median)
            print(f"{role:<8} {path:<42} {median:>10.1f} {p95(timings):>8.1f}")
    print(f"\nSlowest non-chart page median: {max(all_page_medians):.1f} ms")


if __name__ == "__main__":
    main()
