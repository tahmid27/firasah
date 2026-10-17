"""Shared ingestion helpers reused across every source connector.

Each source (JustGiving, LaunchGood, Instagram, TikTok, Mailchimp/Klaviyo)
has its own auth scheme, pagination style, and response shape, so fetching
stays per-connector. But the retry/backoff logic for calling a flaky API and
the "land it in BigQuery" step are identical regardless of source — those
live here so each connector only has to implement what's actually different
about it.
"""

import json
import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

import httpx
from google.cloud import bigquery
from prefect import task

MAX_RETRIES = 5


def parse_retry_after(
    value: str | None, default: float, max_wait: float = 120.0
) -> float:
    """Seconds to wait before retrying, from a Retry-After header.

    HTTP allows two forms: a number of seconds ("30") or a date ("Wed, 21
    Oct 2026 07:28:00 GMT"). Anything unreadable falls back to `default`,
    and the wait is capped at `max_wait` so one odd header can't stall a
    whole refresh for an hour — if the API really needs longer, the retries
    run out and the failure is reported instead.
    """
    if value is None:
        return default
    try:
        seconds = float(value)
    except ValueError:
        try:
            when = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return default
        if when.tzinfo is None:
            when = when.replace(tzinfo=UTC)
        seconds = (when - datetime.now(UTC)).total_seconds()
    return min(max(seconds, 0.0), max_wait)


def request_with_retries(
    client: httpx.Client, method: str, url: str, **kwargs
) -> httpx.Response:
    """Calls a URL with any HTTP method, retrying on transient errors and
    backing off on rate limits. Raises on non-retryable errors (4xx other
    than 429). `**kwargs` (params, json, data, headers, ...) pass straight
    through to httpx — generalised beyond GET because TikTok's video.list
    endpoint requires POST, unlike JustGiving's GET-only donations endpoint.
    """
    for attempt in range(MAX_RETRIES):
        try:
            response = client.request(method, url, **kwargs)
        except httpx.TransportError:
            if attempt == MAX_RETRIES - 1:
                raise
            time.sleep(2**attempt)
            continue

        if response.status_code == 429:
            time.sleep(
                parse_retry_after(response.headers.get("Retry-After"), 2**attempt)
            )
            continue

        if response.status_code >= 500:
            if attempt == MAX_RETRIES - 1:
                response.raise_for_status()
            time.sleep(2**attempt)
            continue

        response.raise_for_status()
        return response

    raise RuntimeError(f"Exceeded {MAX_RETRIES} retries for {url}")


def coerce_to_float(row: dict, dotted_paths: list[str]) -> dict:
    """Forces the named fields (dotted paths into nested dicts, e.g.
    "stats.open_rate") to float, in place; missing or null fields are left
    alone.

    Why: BigQuery schema autodetect types a column from the first values it
    sees. A rate or money amount that happens to arrive as a whole number
    (0, or 1 for 100%) gets typed INTEGER, and the first real fractional
    value (0.43) then fails the load. Sending floats always keeps the
    column FLOAT, whatever the first row is. Use it on any field that is
    conceptually fractional but can arrive as a whole number.
    """
    for path in dotted_paths:
        *parents, key = path.split(".")
        node = row
        for part in parents:
            node = node.get(part) if isinstance(node, dict) else None
            if node is None:
                break
        if isinstance(node, dict) and node.get(key) is not None:
            node[key] = float(node[key])
    return row


def save_raw_json(data: list[dict], path: str | Path) -> None:
    """Dumps a fetch result to disk for local inspection before it's loaded
    to BigQuery. Not a Prefect task — no retry semantics needed for a local
    file write.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))
    print(f"Saved to {path}")


@task(retries=2, retry_delay_seconds=10)
def load_raw_to_bigquery(rows: list[dict], table_id: str, tags: dict) -> None:
    """Appends rows to a raw landing table, tagging each with _ingested_at
    plus whatever source-specific identifiers the caller passes in `tags`
    (e.g. which fundraising page or account they came from). Schema is
    auto-detected from the JSON — the raw layer keeps field names/types
    exactly as the source API sent them; renaming/casting happens later in
    the dbt staging model.

    Retries here are Prefect's own (transient BigQuery/network failures) —
    separate from the source-specific rate-limit/backoff handling in
    get_with_retries, which deals with a different kind of failure.
    """
    if not rows:
        # Deliberate, not an accident: load_table_from_json can't
        # autodetect a schema from an empty list and would fail with a
        # confusing error. Skipping is also the safe choice for
        # refund-aware sources — the previous batch stays the latest one,
        # so an empty response (API hiccup, wrong page) can't mass-
        # invalidate every donation in the snapshot.
        print(f"WARNING: 0 rows to load into {table_id}; skipping load")
        return

    ingested_at = datetime.now(UTC).isoformat()
    tagged_rows = [{**row, **tags, "_ingested_at": ingested_at} for row in rows]

    client = bigquery.Client()
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        autodetect=True,
        # The raw layer mirrors whatever the source sends, so a source
        # adding a field (or us requesting extra metrics) must extend the
        # existing table rather than fail the load on a schema mismatch.
        schema_update_options=[bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION],
    )
    job = client.load_table_from_json(tagged_rows, table_id, job_config=job_config)
    job.result()  # wait for the load job to finish, raises on failure
    print(f"Loaded {len(tagged_rows)} rows into {table_id}")


def update_env_file(updates: dict[str, str], path: str | Path = ".env") -> None:
    """Rewrites specific KEY=VALUE lines in a .env file in place, leaving
    everything else untouched. Needed for OAuth connectors (TikTok first,
    likely others later) whose refresh token rotates every time it's used —
    the old one stops working once it does, so the new one has to be saved
    immediately or the next run breaks.

    Rewrites the whole file content deliberately rather than appending —
    a blind append bit us once before (see CLAUDE.md: appending to a .env
    file missing a trailing newline corrupted the previous line).
    """
    path = Path(path)
    lines = path.read_text().splitlines() if path.exists() else []
    remaining = dict(updates)

    for i, line in enumerate(lines):
        if "=" not in line or line.strip().startswith("#"):
            continue
        key = line.split("=", 1)[0]
        if key in remaining:
            lines[i] = f"{key}={remaining.pop(key)}"

    lines.extend(f"{key}={value}" for key, value in remaining.items())
    path.write_text("\n".join(lines) + "\n")
