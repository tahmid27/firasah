"""Fetches media and account stats from the Instagram Graph API for a
Page-linked Instagram Business Account.

Instagram-specific: auth is a long-lived Page access token (swapped in
scripts/instagram_token_exchange.py — Meta Page tokens don't rotate like
TikTok's refresh token, so no exchange happens on every connector run, just
whenever the 60-day token is getting stale). Pagination is cursor-based via
`paging.next` — a full ready-to-use URL for the next page, unlike
JustGiving's page-number or Mailchimp's offset/count style, so no params
need to be rebuilt by hand between pages. Retry/backoff and the BigQuery
landing step are shared — see ingestion/common.py.
"""

import os
import sys

import httpx
from dotenv import load_dotenv
from prefect import flow, task

from ingestion.common import load_raw_to_bigquery, request_with_retries, save_raw_json

load_dotenv()

ACCESS_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]
BASE_URL = "https://graph.facebook.com/v26.0"

RAW_MEDIA_TABLE_ID = "firasah-dev-511916.firasah_dev.raw_instagram_media"
RAW_ACCOUNT_INFO_TABLE_ID = "firasah-dev-511916.firasah_dev.raw_instagram_account_info"
RAW_MEDIA_INSIGHTS_TABLE_ID = (
    "firasah-dev-511916.firasah_dev.raw_instagram_media_insights"
)

# Per-post metrics only available from the separate insights endpoint (the
# basic /media fields above don't include them). Needs the
# instagram_manage_insights permission, already granted to the app.
INSIGHT_METRICS = "reach,views,shares,saved,total_interactions"


@task
def fetch_account_info(ig_user_id: str) -> dict:
    with httpx.Client(timeout=30) as client:
        response = request_with_retries(
            client,
            "GET",
            f"{BASE_URL}/{ig_user_id}",
            params={
                "fields": "id,username,name,biography,followers_count,"
                "follows_count,media_count,profile_picture_url",
                "access_token": ACCESS_TOKEN,
            },
        )
    return response.json()


@task
def fetch_media(ig_user_id: str) -> list[dict]:
    media = []
    url = f"{BASE_URL}/{ig_user_id}/media"
    params = {
        "fields": "id,caption,media_type,media_product_type,permalink,"
        "timestamp,like_count,comments_count",
        "access_token": ACCESS_TOKEN,
        "limit": 25,
    }

    with httpx.Client(timeout=30) as client:
        while True:
            response = request_with_retries(client, "GET", url, params=params)
            body = response.json()
            media.extend(body["data"])
            print(f"Fetched {len(body['data'])} media items (total so far: {len(media)})")

            next_url = body.get("paging", {}).get("next")
            if not next_url:
                break
            url = next_url
            # `next_url` already has everything (access_token, cursor, ...)
            # baked into its query string — passing params={} here (as
            # opposed to leaving it out / None) makes httpx discard that
            # query string rather than leave it alone, stripping the token.
            params = None

    return media


@task
def fetch_media_insights(media_ids: list[str]) -> list[dict]:
    """One insights call per post (the endpoint has no bulk form).

    A post whose insights Instagram refuses (HTTP 400, e.g. a media type or
    age the metrics don't support) is skipped with a log line rather than
    failing the whole pull — the post still lands via the basic /media
    fetch, it just has no insight row. Other errors (auth, 5xx after
    retries) still raise.
    """
    insights = []
    skipped = 0

    with httpx.Client(timeout=30) as client:
        for media_id in media_ids:
            try:
                response = request_with_retries(
                    client,
                    "GET",
                    f"{BASE_URL}/{media_id}/insights",
                    params={"metric": INSIGHT_METRICS, "access_token": ACCESS_TOKEN},
                )
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 400:
                    raise
                skipped += 1
                print(f"No insights for media {media_id}: {exc.response.text[:200]}")
                continue

            row = {"media_id": media_id}
            for metric in response.json()["data"]:
                row[metric["name"]] = metric["values"][0]["value"]
            insights.append(row)

    print(f"Fetched insights for {len(insights)} posts ({skipped} skipped)")
    return insights


@flow(name="instagram-posts-ingestion")
def instagram_posts_flow(ig_user_id: str) -> None:
    account_info = fetch_account_info(ig_user_id)
    print(
        f"Account info: @{account_info.get('username')} — "
        f"{account_info.get('followers_count')} followers"
    )
    save_raw_json([account_info], "data/raw/instagram_account_info.json")
    load_raw_to_bigquery(
        [account_info], RAW_ACCOUNT_INFO_TABLE_ID, tags={"_ig_user_id": ig_user_id}
    )

    media = fetch_media(ig_user_id)
    print(f"Total media fetched: {len(media)}")
    save_raw_json(media, "data/raw/instagram_media.json")
    load_raw_to_bigquery(media, RAW_MEDIA_TABLE_ID, tags={"_ig_user_id": ig_user_id})

    insights = fetch_media_insights([m["id"] for m in media])
    save_raw_json(insights, "data/raw/instagram_media_insights.json")
    load_raw_to_bigquery(
        insights, RAW_MEDIA_INSIGHTS_TABLE_ID, tags={"_ig_user_id": ig_user_id}
    )


if __name__ == "__main__":
    # Default: the Instagram Business Account ID from .env
    ig_user_id = sys.argv[1] if len(sys.argv) > 1 else os.environ["INSTAGRAM_USER_ID"]
    instagram_posts_flow(ig_user_id)
