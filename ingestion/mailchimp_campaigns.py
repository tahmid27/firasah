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

from ingestion.common import (
    coerce_to_float,
    load_raw_to_bigquery,
    raw_table_id,
    request_with_retries,
    save_raw_json,
)

load_dotenv()

API_KEY = os.environ["MAILCHIMP_API_KEY"]
DATA_CENTER = API_KEY.split("-")[-1]
BASE_URL = f"https://{DATA_CENTER}.api.mailchimp.com/3.0"
PAGE_SIZE = 100

RAW_CAMPAIGN_REPORTS_TABLE_ID = raw_table_id("raw_mailchimp_campaign_reports")
RAW_AUDIENCE_STATS_TABLE_ID = raw_table_id("raw_mailchimp_audience_stats")
RAW_LINK_CLICKS_TABLE_ID = raw_table_id("raw_mailchimp_campaign_link_clicks")
RAW_LIST_ACTIVITY_TABLE_ID = raw_table_id("raw_mailchimp_list_activity_daily")
RAW_LIST_GROWTH_TABLE_ID = raw_table_id("raw_mailchimp_list_growth_monthly")


# Fields that are fractional (rates) or money but can arrive as whole numbers
# (0, or 1 for 100%) — see coerce_to_float for why they are forced to float.
REPORT_FLOAT_FIELDS = [
    "opens.open_rate",
    "opens.proxy_excluded_open_rate",
    "clicks.click_rate",
    "list_stats.open_rate",
    "list_stats.proxy_excluded_open_rate",
    "list_stats.click_rate",
    "list_stats.sub_rate",
    "list_stats.unsub_rate",
    "ecommerce.total_revenue",
    "ecommerce.total_spent",
]
AUDIENCE_FLOAT_FIELDS = [
    "stats.open_rate",
    "stats.click_rate",
    "stats.avg_sub_rate",
    "stats.avg_unsub_rate",
    "stats.target_sub_rate",
]


def _paginated_get(client: httpx.Client, path: str, items_key: str) -> list[dict]:
    """Mailchimp collection endpoints (campaigns, lists, ...) all paginate
    the same way: offset/count params, response includes total_items.
    """
    items = []
    offset = 0

    while True:
        response = request_with_retries(
            client,
            "GET",
            f"{BASE_URL}{path}",
            params={"count": PAGE_SIZE, "offset": offset},
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


def shape_report(report: dict) -> dict:
    return coerce_to_float(report, REPORT_FLOAT_FIELDS)


def shape_audience(audience: dict) -> dict:
    return coerce_to_float(audience, AUDIENCE_FLOAT_FIELDS)


def shape_link_clicks(rows: list[dict]) -> list[dict]:
    # Ratios are fractions, but Mailchimp sends a whole-number 1 when a link
    # got 100% of clicks; forcing float keeps the column FLOAT
    rows = _strip_links(rows)
    for row in rows:
        for field in ("click_percentage", "unique_click_percentage"):
            row[field] = float(row[field])
    return rows


def shape_activity(list_id: str, rows: list[dict]) -> list[dict]:
    return [{"list_id": list_id, **row} for row in rows]


def shape_growth(rows: list[dict]) -> list[dict]:
    return _strip_links(rows)


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
            reports.append(shape_report(response.json()))

    return reports


@task
def fetch_audience_stats() -> list[dict]:
    with httpx.Client(auth=("anystring", API_KEY), timeout=30) as client:
        audiences = _paginated_get(client, "/lists", "lists")
    return [shape_audience(a) for a in audiences]


def _strip_links(rows: list[dict]) -> list[dict]:
    """Mailchimp attaches a `_links` array (API navigation URLs) to every
    record. Nothing uses it, so it is dropped rather than landed."""
    return [{k: v for k, v in row.items() if k != "_links"} for row in rows]


@task
def fetch_link_clicks(campaign_ids: list[str]) -> list[dict]:
    """Which links in each sent campaign were clicked, and how often."""
    rows = []
    with httpx.Client(auth=("anystring", API_KEY), timeout=30) as client:
        for campaign_id in campaign_ids:
            rows.extend(
                _paginated_get(
                    client, f"/reports/{campaign_id}/click-details", "urls_clicked"
                )
            )
    return shape_link_clicks(rows)


@task
def fetch_list_activity(list_ids: list[str]) -> list[dict]:
    """Daily subscribes, unsubscribes and email activity per audience.
    Mailchimp returns a rolling window of recent days, so every run re-pulls
    overlapping days — dbt keeps the latest pull per day."""
    rows = []
    with httpx.Client(auth=("anystring", API_KEY), timeout=30) as client:
        for list_id in list_ids:
            rows.extend(
                shape_activity(
                    list_id,
                    _paginated_get(client, f"/lists/{list_id}/activity", "activity"),
                )
            )
    return rows


@task
def fetch_list_growth(list_ids: list[str]) -> list[dict]:
    """Monthly subscriber growth per audience."""
    rows = []
    with httpx.Client(auth=("anystring", API_KEY), timeout=30) as client:
        for list_id in list_ids:
            rows.extend(
                _paginated_get(client, f"/lists/{list_id}/growth-history", "history")
            )
    return shape_growth(rows)


@flow(name="mailchimp-campaigns-ingestion")
def mailchimp_campaigns_flow(org_id: str) -> None:
    reports = fetch_campaign_reports()
    print(f"Total campaign reports fetched: {len(reports)}")
    save_raw_json(reports, "data/raw/mailchimp_campaign_reports.json")
    load_raw_to_bigquery(reports, RAW_CAMPAIGN_REPORTS_TABLE_ID, tags={}, org_id=org_id)

    audiences = fetch_audience_stats()
    print(f"Total audiences fetched: {len(audiences)}")
    save_raw_json(audiences, "data/raw/mailchimp_audience_stats.json")
    load_raw_to_bigquery(audiences, RAW_AUDIENCE_STATS_TABLE_ID, tags={}, org_id=org_id)

    campaign_ids = [r["id"] for r in reports]
    list_ids = [a["id"] for a in audiences]

    link_clicks = fetch_link_clicks(campaign_ids)
    print(f"Total link-click rows fetched: {len(link_clicks)}")
    save_raw_json(link_clicks, "data/raw/mailchimp_campaign_link_clicks.json")
    load_raw_to_bigquery(link_clicks, RAW_LINK_CLICKS_TABLE_ID, tags={}, org_id=org_id)

    activity = fetch_list_activity(list_ids)
    print(f"Total daily audience-activity rows fetched: {len(activity)}")
    save_raw_json(activity, "data/raw/mailchimp_list_activity_daily.json")
    load_raw_to_bigquery(activity, RAW_LIST_ACTIVITY_TABLE_ID, tags={}, org_id=org_id)

    growth = fetch_list_growth(list_ids)
    print(f"Total monthly growth rows fetched: {len(growth)}")
    save_raw_json(growth, "data/raw/mailchimp_list_growth_monthly.json")
    load_raw_to_bigquery(growth, RAW_LIST_GROWTH_TABLE_ID, tags={}, org_id=org_id)


if __name__ == "__main__":
    mailchimp_campaigns_flow(os.environ["FIRASAH_ORG_ID"])
