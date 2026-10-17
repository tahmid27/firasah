"""Parent flow: refresh every source, then rebuild the dbt models.

Order matters: all ingestion has to finish before dbt runs, because the
models read the raw tables the connectors land. Each source is isolated —
one connector failing (e.g. an expired Instagram token) doesn't stop the
others from loading. dbt still runs on whatever landed, and the flow fails
at the end so the failure is visible rather than swallowed.

Run once by hand:   uv run python -m ingestion.refresh
Run on a schedule:  uv run python -m ingestion.refresh --serve
"""

import hashlib
import os
import subprocess
import sys
from pathlib import Path

from prefect import flow, task

from ingestion.instagram_posts import instagram_posts_flow
from ingestion.justgiving_donations import justgiving_donations_flow
from ingestion.launchgood_donations import launchgood_donations_flow
from ingestion.mailchimp_campaigns import mailchimp_campaigns_flow
from ingestion.tiktok_videos import tiktok_videos_flow

LAUNCHGOOD_EXPORT_PATH = "data/raw/launchgood_export.csv"
LAUNCHGOOD_STATE_PATH = Path("data/state/launchgood_last_loaded.sha256")

DBT_ARGS = ["--project-dir", "dbt", "--profiles-dir", str(Path("~/.dbt").expanduser())]


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_source(name: str, fn, failures: list[str], *args) -> bool:
    """Runs one connector flow; records the failure instead of raising."""
    try:
        fn(*args)
        return True
    except Exception as exc:  # noqa: BLE001 — isolation is the point
        print(f"[refresh] {name} FAILED: {exc!r}")
        failures.append(name)
        return False


def _launchgood_has_new_export() -> bool:
    export = Path(LAUNCHGOOD_EXPORT_PATH)
    if not export.exists():
        print("[refresh] launchgood: no export file, skipping")
        return False
    if (
        LAUNCHGOOD_STATE_PATH.exists()
        and LAUNCHGOOD_STATE_PATH.read_text().strip() == _file_hash(export)
    ):
        print("[refresh] launchgood: export unchanged since last load, skipping")
        return False
    return True


def _mark_launchgood_loaded() -> None:
    LAUNCHGOOD_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    LAUNCHGOOD_STATE_PATH.write_text(_file_hash(Path(LAUNCHGOOD_EXPORT_PATH)) + "\n")


@task
def run_dbt(command: str) -> None:
    """Runs a dbt command; a non-zero exit (failed model/test) fails the task."""
    result = subprocess.run(
        ["uv", "run", "dbt", command, *DBT_ARGS], capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError(f"dbt {command} failed (exit {result.returncode})")


@flow(name="firasah-refresh")
def firasah_refresh_flow(
    event_id: str | None = None,
    ig_user_id: str | None = None,
) -> None:
    # Defaults come from .env so no account identifiers live in source code
    event_id = event_id or os.environ["JUSTGIVING_EVENT_ID"]
    ig_user_id = ig_user_id or os.environ["INSTAGRAM_USER_ID"]
    failures: list[str] = []

    _run_source("justgiving", justgiving_donations_flow, failures, event_id)
    _run_source("tiktok", tiktok_videos_flow, failures)
    _run_source("instagram", instagram_posts_flow, failures, ig_user_id)
    _run_source("mailchimp", mailchimp_campaigns_flow, failures)

    if _launchgood_has_new_export() and _run_source(
        "launchgood", launchgood_donations_flow, failures, LAUNCHGOOD_EXPORT_PATH
    ):
        _mark_launchgood_loaded()

    try:
        run_dbt("snapshot")
        run_dbt("run")
        run_dbt("test")
    finally:
        if failures:
            print(f"[refresh] sources that failed to load: {', '.join(failures)}")

    if failures:
        raise RuntimeError(f"Refresh finished with failed sources: {failures}")


if __name__ == "__main__":
    if "--serve" in sys.argv:
        # Blocks forever, triggering the flow daily at 06:00 UK time.
        firasah_refresh_flow.serve(
            name="firasah-daily-refresh", cron="0 6 * * *", timezone="Europe/London"
        )
    else:
        firasah_refresh_flow()
