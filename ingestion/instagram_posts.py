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

RAW_MEDIA_TABLE_ID = "firasah-dev.firasah_dev.raw_instagram_media"
RAW_ACCOUNT_INFO_TABLE_ID = "firasah-dev.firasah_dev.raw_instagram_account_info"


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


if __name__ == "__main__":
    # Default: the Instagram Business Account linked to the "Firasah" Page,
    # which is itself linked to the real TestBusiness Instagram account.
    ig_user_id = sys.argv[1] if len(sys.argv) > 1 else "17840000000000000"
    instagram_posts_flow(ig_user_id)
