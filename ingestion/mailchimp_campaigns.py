"""Fetches campaign performance and audience stats from the Mailchimp
Marketing API v3.

Mailchimp-specific: the API key itself encodes its data center (e.g.
...-us14), so the base URL is parsed straight out of the key rather than
stored separately. Auth is HTTP Basic (any username, key as password) —
different from JustGiving's header-based key and TikTok's Bearer token.
Pagination is offset/count based, unlike JustGiving's page-number or
TikTok's cursor style. Retry/backoff and the BigQuery landing step are
shared — see ingestion/common.py.
"""

import os

import httpx
from dotenv import load_dotenv
from prefect import flow, task

from ingestion.common import load_raw_to_bigquery, request_with_retries, save_raw_json

load_dotenv()

API_KEY = os.environ["MAILCHIMP_API_KEY"]
DATA_CENTER = API_KEY.split("-")[-1]
BASE_URL = f"https://{DATA_CENTER}.api.mailchimp.com/3.0"
PAGE_SIZE = 100

RAW_CAMPAIGN_REPORTS_TABLE_ID = "firasah-dev-511916.firasah_dev.raw_mailchimp_campaign_reports"
RAW_AUDIENCE_STATS_TABLE_ID = "firasah-dev-511916.firasah_dev.raw_mailchimp_audience_stats"


def _paginated_get(client: httpx.Client, path: str, items_key: str) -> list[dict]:
    """Mailchimp collection endpoints (campaigns, lists, ...) all paginate
    the same way: offset/count params, response includes total_items.
    """
    items = []
    offset = 0

    while True:
        response = request_with_retries(
            client, "GET", f"{BASE_URL}{path}", params={"count": PAGE_SIZE, "offset": offset}
        )
        body = response.json()
        items.extend(body[items_key])
        print(
            f"Fetched {len(body[items_key])} {items_key} "
            f"(offset={offset}, total={body['total_items']})"
        )

        offset += PAGE_SIZE
        if offset >= body["total_items"]:
            break

    return items


@task
def fetch_campaign_reports() -> list[dict]:
    """Only campaigns that have actually sent have report data — drafts
    (status == "save") have nothing to fetch from the reports endpoint.
    """
    with httpx.Client(auth=("anystring", API_KEY), timeout=30) as client:
        campaigns = _paginated_get(client, "/campaigns", "campaigns")
        sent_campaigns = [c for c in campaigns if c["status"] == "sent"]
        print(f"{len(sent_campaigns)} of {len(campaigns)} campaigns have actually sent")

        reports = []
        for campaign in sent_campaigns:
            response = request_with_retries(
                client, "GET", f"{BASE_URL}/reports/{campaign['id']}"
            )
            reports.append(response.json())

    return reports


@task
def fetch_audience_stats() -> list[dict]:
    with httpx.Client(auth=("anystring", API_KEY), timeout=30) as client:
        return _paginated_get(client, "/lists", "lists")


@flow(name="mailchimp-campaigns-ingestion")
def mailchimp_campaigns_flow() -> None:
    reports = fetch_campaign_reports()
    print(f"Total campaign reports fetched: {len(reports)}")
    save_raw_json(reports, "data/raw/mailchimp_campaign_reports.json")
    load_raw_to_bigquery(reports, RAW_CAMPAIGN_REPORTS_TABLE_ID, tags={})

    audiences = fetch_audience_stats()
    print(f"Total audiences fetched: {len(audiences)}")
    save_raw_json(audiences, "data/raw/mailchimp_audience_stats.json")
    load_raw_to_bigquery(audiences, RAW_AUDIENCE_STATS_TABLE_ID, tags={})


if __name__ == "__main__":
    mailchimp_campaigns_flow()
