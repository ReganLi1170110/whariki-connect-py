"""Python -> R subprocess integration tests (proposal section 4.2).

Each of the four ggplot2 scripts is run through app.r_runner exactly as the
web app runs it, with three dataset sizes: empty, a single row, and a large
dataset. A pass means R returned a valid PNG within the runner's 30-second
timeout. These tests are skipped automatically if R is not installed.
"""
import shutil
import time
from datetime import date, timedelta

import pytest

from app import r_runner

pytestmark = pytest.mark.skipif(
    shutil.which("Rscript") is None and not __import__("os").environ.get("RSCRIPT_PATH"),
    reason="R / Rscript not installed",
)

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
STRANDS = ["Wellbeing", "Belonging", "Contribution", "Communication", "Exploration"]


def _weeks(n):
    start = date(2016, 1, 4)
    return [(start + timedelta(weeks=i)).isoformat() for i in range(n)]


SCRIPTS = {
    "strand_coverage.R": {
        "fields": ["strand", "count"],
        "single": [{"strand": "Wellbeing", "count": 1}],
        # The real query always returns the five strands, so "large" means large counts.
        "large": [{"strand": s, "count": 10_000 + i} for i, s in enumerate(STRANDS)],
    },
    "attendance_trend.R": {
        "fields": ["week_start", "present_pct"],
        "single": [{"week_start": "2026-09-21", "present_pct": 92.5}],
        "large": [{"week_start": w, "present_pct": 60 + (i % 40)} for i, w in enumerate(_weeks(520))],
    },
    "accident_frequency.R": {
        "fields": ["nature", "count"],
        "single": [{"nature": "Bruise", "count": 1}],
        "large": [{"nature": f"Injury type {i}", "count": 500 - i} for i in range(60)],
    },
    "routine_trend.R": {
        "fields": ["week_start", "meal_score", "toileting_issue_pct"],
        "single": [{"week_start": "2026-09-21", "meal_score": 66.0, "toileting_issue_pct": 10.0}],
        "large": [{"week_start": w, "meal_score": (i * 7) % 100, "toileting_issue_pct": (i * 3) % 50}
                  for i, w in enumerate(_weeks(520))],
    },
}

CASES = [(script, size) for script in SCRIPTS for size in ("empty", "single", "large")]


@pytest.mark.parametrize("script, size", CASES, ids=[f"{s}-{z}" for s, z in CASES])
def test_r_script_returns_png(script, size):
    spec = SCRIPTS[script]
    rows = [] if size == "empty" else spec[size]

    started = time.perf_counter()
    png = r_runner.run_chart_script(script, rows, spec["fields"], "chart.png", title=f"pytest {size}")
    elapsed = time.perf_counter() - started

    assert png.startswith(PNG_MAGIC), "R did not return a PNG"
    assert len(png) > 1000
    assert elapsed < 30


def test_wrong_columns_raise_a_readable_error():
    with pytest.raises(r_runner.RScriptError) as err:
        r_runner.run_chart_script("attendance_trend.R", [{"x": 1}], ["x"], "chart.png")
    assert "week_start" in err.value.message
