# R Chart Runner
#
# Runs the .R scripts in app/../analytics/ via subprocess and returns the
# PNG bytes. Follows the same "degrade gracefully, tell the user exactly
# what to install" pattern already used for the AI assistant (see
# app/ai_assistant.py) rather than letting a missing R install crash the
# whole analytics page.

import glob
import os
import shutil
import subprocess
import tempfile
import csv

ANALYTICS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'analytics')


class RNotConfigured(Exception):
    """R itself, or a required package, isn't available. Message is meant
    to be shown directly to the user (an admin/teacher), with install steps."""
    def __init__(self, message):
        super().__init__(message)
        self.message = message


class RScriptError(Exception):
    """R was found and ran, but the script itself failed - a real bug,
    not a missing-dependency situation."""
    def __init__(self, message):
        super().__init__(message)
        self.message = message


def find_rscript():
    """Locates the Rscript executable. Checks, in order: an explicit
    RSCRIPT_PATH environment variable (for unusual installs), the system
    PATH, then the standard Windows install location, since R's Windows
    installer does not add itself to PATH by default."""
    override = os.environ.get("RSCRIPT_PATH", "").strip()
    if override:
        if os.path.isfile(override):
            return override
        raise RNotConfigured(
            f"RSCRIPT_PATH is set to \"{override}\" but no file exists there. "
            "Check the path, or unset RSCRIPT_PATH to let it auto-detect."
        )

    on_path = shutil.which("Rscript")
    if on_path:
        return on_path

    # Windows: R does not add itself to PATH by default. Look in the
    # standard install location for any version.
    for pattern in (
        r"C:\Program Files\R\R-*\bin\Rscript.exe",
        r"C:\Program Files\R\R-*\bin\x64\Rscript.exe",
    ):
        matches = sorted(glob.glob(pattern), reverse=True)  # newest version first
        if matches:
            return matches[0]

    raise RNotConfigured(
        "R isn't installed, or Rscript isn't on PATH.\n\n"
        "Install R from https://cran.r-project.org (Windows: run the installer "
        "with default options), then install ggplot2 by opening R and running:\n"
        "    install.packages(\"ggplot2\")\n\n"
        "If R is installed somewhere non-standard, set the RSCRIPT_PATH "
        "environment variable to the full path of Rscript.exe."
    )


def run_chart_script(script_name, rows, fieldnames, output_name, title=""):
    """Writes `rows` to a temp CSV, runs analytics/<script_name> against it,
    and returns the resulting PNG as bytes.

    rows: list of dicts. fieldnames: CSV column order (must match what the
    R script expects - see the comment at the top of each .R file).
    """
    rscript = find_rscript()  # raises RNotConfigured if missing - let it propagate

    script_path = os.path.join(ANALYTICS_DIR, script_name)
    if not os.path.isfile(script_path):
        raise RScriptError(f"Analytics script not found: {script_name}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        csv_path = os.path.join(tmp_dir, "input.csv")
        png_path = os.path.join(tmp_dir, output_name)

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            # extrasaction='ignore': a repository query may return extra
            # columns for its own bookkeeping - only the declared
            # fieldnames need to reach the R script.
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(rows)

        result = subprocess.run(
            [rscript, script_path, csv_path, png_path, title],
            capture_output=True, text=True, timeout=30,
        )

        if result.returncode != 0:
            # Surface R's own error message rather than a bare "failed" -
            # same principle as showing the AI provider's raw error text.
            detail = (result.stderr or result.stdout or "").strip()
            raise RScriptError(
                f"The R script exited with an error.\n\n{detail}"
            )

        if not os.path.isfile(png_path):
            raise RScriptError("The R script ran but did not produce a chart file.")

        with open(png_path, "rb") as f:
            return f.read()
