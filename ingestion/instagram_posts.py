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
from datetime import datetime, timedelta, timezone

import httpx
from dotenv import load_dotenv
from prefect import flow, task

from ingestion.common import (
    coerce_to_float,
    load_raw_to_bigquery,
    request_with_retries,
    save_raw_json,
)

load_dotenv()

ACCESS_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]
BASE_URL = "https://graph.facebook.com/v26.0"

RAW_MEDIA_TABLE_ID = "firasah-dev-511916.firasah_dev.raw_instagram_media"
RAW_ACCOUNT_INFO_TABLE_ID = "firasah-dev-511916.firasah_dev.raw_instagram_account_info"
RAW_MEDIA_INSIGHTS_TABLE_ID = (
    "firasah-dev-511916.firasah_dev.raw_instagram_media_insights"
)

RAW_ACCOUNT_INSIGHTS_TABLE_ID = (
    "firasah-dev-511916.firasah_dev.raw_instagram_account_insights_daily"
)
RAW_FOLLOWER_DEMOGRAPHICS_TABLE_ID = (
    "firasah-dev-511916.firasah_dev.raw_instagram_follower_demographics"
)

# Per-post metrics only available from the separate insights endpoint (the
# basic /media fields above don't include them). Needs the
# instagram_manage_insights permission, already granted to the app.
# Requesting a metric the media type doesn't support fails the WHOLE call,
# so the list depends on the format: feed posts (images/carousels) support
# profile_visits and follows; Reels support watch-time metrics instead.
BASE_INSIGHT_METRICS = "reach,views,shares,saved,total_interactions,reposts"
EXTRA_INSIGHT_METRICS = {
    "FEED": "profile_visits,follows",
    "REELS": "ig_reels_avg_watch_time,ig_reels_video_view_total_time,reels_skip_rate",
}

# Account-level daily totals. All support metric_type=total_value over a
# since/until window; pulled one day at a time to get a per-day series.
ACCOUNT_DAILY_METRICS = (
    "reach,views,accounts_engaged,likes,comments,shares,saves,reposts,"
    "total_interactions,profile_links_taps"
)
FOLLOWER_DEMOGRAPHIC_BREAKDOWNS = ["age", "gender", "country", "city"]


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
def fetch_media_insights(media: list[dict]) -> list[dict]:
    """One insights call per post (the endpoint has no bulk form).

    Asks for format-specific extras (see EXTRA_INSIGHT_METRICS); if
    Instagram rejects that combination it falls back to the base metrics.
    A post whose insights Instagram refuses outright (HTTP 400, e.g. it
    predates the account becoming a business account) is skipped with a log
    line rather than failing the pull — it still lands via the basic /media
    fetch, just with no insight row. Other errors (auth, 5xx after
    retries) still raise.
    """
    insights = []
    skipped = 0

    def call(client, media_id, metrics):
        return request_with_retries(
            client,
            "GET",
            f"{BASE_URL}/{media_id}/insights",
            params={"metric": metrics, "access_token": ACCESS_TOKEN},
        )

    with httpx.Client(timeout=30) as client:
        for item in media:
            media_id = item["id"]
            extra = EXTRA_INSIGHT_METRICS.get(item.get("media_product_type"))
            attempts = [f"{BASE_INSIGHT_METRICS},{extra}"] if extra else []
            attempts.append(BASE_INSIGHT_METRICS)

            response = None
            for metrics in attempts:
                try:
                    response = call(client, media_id, metrics)
                    break
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code != 400:
                        raise
                    last_error = exc.response.text[:200]

            if response is None:
                skipped += 1
                print(f"No insights for media {media_id}: {last_error}")
                continue

            row = {"media_id": media_id}
            for metric in response.json()["data"]:
                row[metric["name"]] = metric["values"][0]["value"]
            # A percentage that can arrive as a whole number (e.g. 5); see
            # coerce_to_float for why it must stay a float.
            insights.append(coerce_to_float(row, ["reels_skip_rate"]))

    print(f"Fetched insights for {len(insights)} posts ({skipped} skipped)")
    return insights


@task
def fetch_account_insights_daily(ig_user_id: str, days: int) -> list[dict]:
    """Account-level totals for each of the last `days` complete days.

    Complete days only (today is partial and would be understated). Each
    run re-pulls the recent window, so the same day can land more than once
    — dbt keeps the latest pull per day. Instagram can lag up to 48 hours,
    which is also why overlapping windows are worth re-pulling.
    """
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    rows = []

    with httpx.Client(timeout=30) as client:
        for offset in range(days, 0, -1):
            day = today - timedelta(days=offset)
            response = request_with_retries(
                client,
                "GET",
                f"{BASE_URL}/{ig_user_id}/insights",
                params={
                    "metric": ACCOUNT_DAILY_METRICS,
                    "metric_type": "total_value",
                    "period": "day",
                    "since": int(day.timestamp()),
                    "until": int((day + timedelta(days=1)).timestamp()),
                    "access_token": ACCESS_TOKEN,
                },
            )
            row = {"date": day.date().isoformat()}
            for metric in response.json()["data"]:
                row[metric["name"]] = metric["total_value"]["value"]
            rows.append(row)

    print(f"Fetched account insights for {len(rows)} days")
    return rows


@task
def fetch_follower_demographics(ig_user_id: str) -> list[dict]:
    """Who the followers are, one row per (breakdown, bucket). A snapshot
    per run — demographics shift slowly, and the history is the trend.
    Needs 100+ followers; if Instagram refuses a breakdown it is skipped.
    Only top-45 buckets are returned per breakdown (Instagram's cap).
    """
    rows = []
    with httpx.Client(timeout=30) as client:
        for breakdown in FOLLOWER_DEMOGRAPHIC_BREAKDOWNS:
            try:
                response = request_with_retries(
                    client,
                    "GET",
                    f"{BASE_URL}/{ig_user_id}/insights",
                    params={
                        "metric": "follower_demographics",
                        "metric_type": "total_value",
                        "period": "lifetime",
                        "timeframe": "this_month",
                        "breakdown": breakdown,
                        "access_token": ACCESS_TOKEN,
                    },
                )
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 400:
                    raise
                print(f"No follower demographics by {breakdown}: {exc.response.text[:200]}")
                continue

            for data in response.json()["data"]:
                for breakdown_block in data["total_value"].get("breakdowns", []):
                    for result in breakdown_block["results"]:
                        rows.append(
                            {
                                "breakdown": breakdown,
                                "bucket": result["dimension_values"][0],
                                "followers": result["value"],
                            }
                        )

    print(f"Fetched {len(rows)} follower demographic buckets")
    return rows


@flow(name="instagram-posts-ingestion")
def instagram_posts_flow(ig_user_id: str, account_insights_days: int = 7) -> None:
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

    insights = fetch_media_insights(media)
    save_raw_json(insights, "data/raw/instagram_media_insights.json")
    load_raw_to_bigquery(
        insights, RAW_MEDIA_INSIGHTS_TABLE_ID, tags={"_ig_user_id": ig_user_id}
    )

    daily = fetch_account_insights_daily(ig_user_id, account_insights_days)
    save_raw_json(daily, "data/raw/instagram_account_insights_daily.json")
    load_raw_to_bigquery(
        daily, RAW_ACCOUNT_INSIGHTS_TABLE_ID, tags={"_ig_user_id": ig_user_id}
    )

    demographics = fetch_follower_demographics(ig_user_id)
    save_raw_json(demographics, "data/raw/instagram_follower_demographics.json")
    load_raw_to_bigquery(
        demographics,
        RAW_FOLLOWER_DEMOGRAPHICS_TABLE_ID,
        tags={"_ig_user_id": ig_user_id},
    )


if __name__ == "__main__":
    # Default: the Instagram Business Account ID from .env
    # Optional second arg: how many past days of account insights to pull
    # (default 7; use e.g. 60 once to backfill history).
    ig_user_id = sys.argv[1] if len(sys.argv) > 1 else os.environ["INSTAGRAM_USER_ID"]
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    instagram_posts_flow(ig_user_id, days)
