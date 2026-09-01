"""Fetches all donations for a JustGiving fundraising page.

Real Phase 2 ingestion script (as opposed to the seed-based practice rep):
walks every page of the donations endpoint, retrying on transient errors
and backing off on rate limits, and stops on non-retryable errors (e.g. a
fundraising page that doesn't exist).
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()

BASE_URL = "https://api.staging.justgiving.com"
APP_ID = os.environ["JUSTGIVING_APP_ID"]
PAGE_SIZE = 100
MAX_RETRIES = 5

RAW_TABLE_ID = "firasah-dev.firasah_dev.raw_justgiving_donations"


def _get_with_retries(client: httpx.Client, url: str, params: dict) -> httpx.Response:
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


def fetch_donations(page_short_name: str) -> list[dict]:
    url = f"{BASE_URL}/v2/fundraising/pages/{page_short_name}/donations"
    donations = []

    with httpx.Client(
        headers={"x-api-key": APP_ID, "Accept": "application/json"}, timeout=30
    ) as client:
        page_number = 1
        while True:
            response = _get_with_retries(
                client, url, params={"pageNumber": page_number, "pageSize": PAGE_SIZE}
            )
            body = response.json()
            donations.extend(body["donations"])

            total_pages = body["pagination"]["totalPages"]
            print(
                f"Fetched page {page_number}/{total_pages} "
                f"({len(body['donations'])} donations)"
            )

            if page_number >= total_pages:
                break
            page_number += 1

    return donations


def load_to_bigquery(donations: list[dict], page_short_name: str) -> None:
    """Appends fetched donations to the raw landing table, tagged with when
    and which page they came from. Schema is auto-detected from the JSON —
    this is the raw layer, so field names/types stay exactly as the API
    sent them; renaming and casting happens later in the dbt staging model.
    """
    ingested_at = datetime.now(timezone.utc).isoformat()
    rows = [
        {**donation, "_page_short_name": page_short_name, "_ingested_at": ingested_at}
        for donation in donations
    ]

    client = bigquery.Client()
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        autodetect=True,
    )
    job = client.load_table_from_json(rows, RAW_TABLE_ID, job_config=job_config)
    job.result()  # wait for the load job to finish, raises on failure
    print(f"Loaded {len(rows)} rows into {RAW_TABLE_ID}")


if __name__ == "__main__":
    page_short_name = sys.argv[1] if len(sys.argv) > 1 else "example-fundraising-page"
    donations = fetch_donations(page_short_name)
    print(f"Total donations fetched: {len(donations)}")

    out_path = Path("data/raw/justgiving_donations.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(donations, indent=2))
    print(f"Saved to {out_path}")

    load_to_bigquery(donations, page_short_name)
