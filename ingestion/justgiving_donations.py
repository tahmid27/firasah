"""Fetches all donations for a JustGiving fundraising page.

Real Phase 2 ingestion script (as opposed to the seed-based practice rep):
walks every page of the donations endpoint, retrying on transient errors
and backing off on rate limits, and stops on non-retryable errors (e.g. a
fundraising page that doesn't exist).

JustGiving-specific: auth header, base URL, and page-number pagination.
Retry/backoff and the BigQuery landing step are shared — see
ingestion/common.py.
"""

import os
import sys

import httpx
from dotenv import load_dotenv
from prefect import flow, task

from ingestion.common import load_raw_to_bigquery, request_with_retries, save_raw_json

load_dotenv()

BASE_URL = "https://api.staging.justgiving.com"
APP_ID = os.environ["JUSTGIVING_APP_ID"]
PAGE_SIZE = 100

RAW_TABLE_ID = "firasah-dev-511916.firasah_dev.raw_justgiving_donations"


@task
def fetch_donations(page_short_name: str) -> list[dict]:
    url = f"{BASE_URL}/v2/fundraising/pages/{page_short_name}/donations"
    donations = []

    with httpx.Client(
        headers={"x-api-key": APP_ID, "Accept": "application/json"}, timeout=30
    ) as client:
        page_number = 1
        while True:
            response = request_with_retries(
                client,
                "GET",
                url,
                params={"pageNumber": page_number, "pageSize": PAGE_SIZE},
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


@flow(name="justgiving-donations-ingestion")
def justgiving_donations_flow(page_short_name: str) -> None:
    donations = fetch_donations(page_short_name)
    print(f"Total donations fetched: {len(donations)}")

    save_raw_json(donations, "data/raw/justgiving_donations.json")

    load_raw_to_bigquery(
        donations, RAW_TABLE_ID, tags={"_page_short_name": page_short_name}
    )


if __name__ == "__main__":
    page_short_name = (
        sys.argv[1] if len(sys.argv) > 1 else os.environ["JUSTGIVING_PAGE_SHORT_NAME"]
    )
    justgiving_donations_flow(page_short_name)
