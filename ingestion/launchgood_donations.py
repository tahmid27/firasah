"""Parses a LaunchGood donor-report export into raw rows.

LaunchGood has no public API (confirmed, see CLAUDE.md) — ingestion here is
a manual export someone downloads from a fundraiser's "Download report"
action (fundraiser page -> Donors tab), not a live API pull. This connector's
job is narrower than every other source's: parse whatever columns the real
export contains and land them in BigQuery the same way an API response
would be. Column headers in the real export have spaces/parentheses (e.g.
"Donation Amount (in Donation Currency)"), which BigQuery's column-name
rules don't allow, so they're sanitised to snake_case before loading — the
dbt staging model still renames/casts from there like every other source.
"""

import re
import sys
from datetime import date, datetime, time
from pathlib import Path

import openpyxl
from prefect import flow, task

from ingestion.common import load_raw_to_bigquery, save_raw_json

RAW_TABLE_ID = "firasah-dev.firasah_dev.raw_launchgood_donations"


def _sanitize_column_name(header: str) -> str:
    return re.sub(r"[^0-9a-zA-Z]+", "_", header).strip("_").lower()


def _serialize_value(value):
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    return value


@task
def read_donations_export(path: str | Path) -> list[dict]:
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active

    rows = ws.iter_rows(values_only=True)
    headers = [_sanitize_column_name(header) for header in next(rows)]

    donations = []
    for row in rows:
        if all(cell is None for cell in row):
            continue
        donations.append(
            {header: _serialize_value(value) for header, value in zip(headers, row)}
        )
    return donations


@flow(name="launchgood-donations-ingestion")
def launchgood_donations_flow(path: str) -> None:
    donations = read_donations_export(path)
    print(f"Parsed {len(donations)} donations from {path}")

    save_raw_json(donations, "data/raw/launchgood_donations.json")

    load_raw_to_bigquery(
        donations, RAW_TABLE_ID, tags={"_source_file": Path(path).name}
    )


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data/raw/launchgood_export.xlsx"
    launchgood_donations_flow(path)
