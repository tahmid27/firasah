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
RAW_PAGES_TABLE_ID = "firasah-dev-511916.firasah_dev.raw_justgiving_pages"


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


@task
def fetch_page_details(page_short_name: str) -> dict:
    """Page-level details (owner, parent event, target, status, totals).

    The donations endpoint only knows which page a donation went to; the
    larger event/appeal a page belongs to, and its fundraising target, live
    on the page endpoint. Kept to scalar fields plus the charity's id/name:
    the full response also carries page story HTML, images and empty
    containers (e.g. `"teams": []`) that BigQuery can't infer a type for
    and nothing downstream needs.
    """
    with httpx.Client(
        headers={"x-api-key": APP_ID, "Accept": "application/json"}, timeout=30
    ) as client:
        response = request_with_retries(
            client, "GET", f"{BASE_URL}/v1/fundraising/pages/{page_short_name}"
        )
    body = response.json()

    page = {
        key: value
        for key, value in body.items()
        if value is not None and not isinstance(value, (dict, list))
    }
    charity = body.get("charity") or {}
    page["charity"] = {"id": charity.get("id"), "name": charity.get("name")}
    return page


@task
def fetch_event_page_names(event_id: str) -> list[str]:
    """Every fundraising page under a JustGiving event (the larger
    project/appeal), so one configured event covers all of its fundraisers
    instead of listing pages by hand. Paginated with `page`/`pagesize`
    (this endpoint's names — not the `pageNumber` the donations endpoint
    uses); the response says how many pages there are.
    """
    names = []
    page = 1

    with httpx.Client(
        headers={"x-api-key": APP_ID, "Accept": "application/json"}, timeout=30
    ) as client:
        while True:
            response = request_with_retries(
                client,
                "GET",
                f"{BASE_URL}/v1/event/{event_id}/pages",
                params={"page": page, "pagesize": PAGE_SIZE},
            )
            body = response.json()
            names.extend(p["pageShortName"] for p in body["fundraisingPages"])

            if page >= body["totalPages"]:
                break
            page += 1

    print(f"Event {event_id}: {len(names)} fundraising pages")
    return names


@flow(name="justgiving-donations-ingestion")
def justgiving_donations_flow(event_id: str) -> None:
    page_names = fetch_event_page_names(event_id)

    # Fetch everything before loading anything: a failed fetch then lands
    # zero rows for that page, so the snapshot never sees a half-finished
    # pull (see justgiving_donations_snapshot). One page failing doesn't
    # stop the others — its previous batch simply stays the latest one,
    # which is the safe direction (stale, never falsely refunded).
    fetched: dict[str, tuple[list[dict], dict]] = {}
    failures: list[str] = []
    for name in page_names:
        try:
            donations = fetch_donations(name)
            page = fetch_page_details(name)
        except Exception as exc:  # noqa: BLE001 — per-page isolation
            print(f"[justgiving] page {name} FAILED: {exc!r}")
            failures.append(name)
            continue
        print(f"Page {name!r}: {len(donations)} donations (event: {page.get('eventName')!r})")
        fetched[name] = (donations, page)

    all_donations = [d for donations, _ in fetched.values() for d in donations]
    save_raw_json(all_donations, "data/raw/justgiving_donations.json")
    save_raw_json([page for _, page in fetched.values()], "data/raw/justgiving_pages.json")

    for name, (donations, page) in fetched.items():
        tags = {"_page_short_name": name}
        load_raw_to_bigquery(donations, RAW_TABLE_ID, tags=tags)
        load_raw_to_bigquery([page], RAW_PAGES_TABLE_ID, tags=tags)

    if failures:
        raise RuntimeError(f"JustGiving pages that failed to fetch: {failures}")


if __name__ == "__main__":
    # Argument: the JustGiving event ID (default from .env). Every fundraising
    # page under that event is pulled.
    event_id = sys.argv[1] if len(sys.argv) > 1 else os.environ["JUSTGIVING_EVENT_ID"]
    justgiving_donations_flow(event_id)
