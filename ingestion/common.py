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
from datetime import datetime, timezone
from pathlib import Path

import httpx
from google.cloud import bigquery
from prefect import task

MAX_RETRIES = 5


def get_with_retries(client: httpx.Client, url: str, params: dict) -> httpx.Response:
    """GETs a URL, retrying on transient errors and backing off on rate
    limits. Raises on non-retryable errors (4xx other than 429).
    """
    for attempt in range(MAX_RETRIES):
        try:
            response = client.get(url, params=params)
        except httpx.TransportError:
            if attempt == MAX_RETRIES - 1:
                raise
            time.sleep(2**attempt)
            continue

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 2**attempt))
            time.sleep(retry_after)
            continue

        if response.status_code >= 500:
            if attempt == MAX_RETRIES - 1:
                response.raise_for_status()
            time.sleep(2**attempt)
            continue

        response.raise_for_status()
        return response

    raise RuntimeError(f"Exceeded {MAX_RETRIES} retries for {url}")


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
    ingested_at = datetime.now(timezone.utc).isoformat()
    tagged_rows = [{**row, **tags, "_ingested_at": ingested_at} for row in rows]

    client = bigquery.Client()
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        autodetect=True,
    )
    job = client.load_table_from_json(tagged_rows, table_id, job_config=job_config)
    job.result()  # wait for the load job to finish, raises on failure
    print(f"Loaded {len(tagged_rows)} rows into {table_id}")
