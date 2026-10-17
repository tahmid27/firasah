"""Fetches recent videos and account-level stats for a TikTok account via
the Display API (v2), authenticated through TikTok's OAuth flow.

TikTok-specific: OAuth token refresh. Access tokens expire every 24 hours;
the refresh token that replaces them lasts 365 days but *rotates* on every
use, so the new one is written straight back to .env via
ingestion.common.update_env_file — otherwise the next run breaks. Refreshing
happens unconditionally at the start of every run rather than waiting for a
401, which is simpler and cheap enough for a manually-run/scheduled flow.

Pagination style (POST + cursor) and response shape are also TikTok-specific.
Retry/backoff and the BigQuery landing step are shared — see
ingestion/common.py.
"""

import os

import httpx
from dotenv import load_dotenv
from prefect import flow, task

from ingestion.common import (
    load_raw_to_bigquery,
    request_with_retries,
    save_raw_json,
    update_env_file,
)

load_dotenv()

TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
VIDEO_LIST_URL = "https://open.tiktokapis.com/v2/video/list/"
USER_INFO_URL = "https://open.tiktokapis.com/v2/user/info/"

VIDEO_FIELDS = (
    "id,title,video_description,create_time,duration,cover_image_url,"
    "share_url,view_count,like_count,comment_count,share_count"
)
USER_FIELDS = "open_id,display_name,follower_count,following_count,likes_count,video_count"

RAW_VIDEOS_TABLE_ID = "firasah-dev-511916.firasah_dev.raw_tiktok_videos"
RAW_USER_INFO_TABLE_ID = "firasah-dev-511916.firasah_dev.raw_tiktok_user_info"


@task
def refresh_access_token() -> str:
    with httpx.Client(timeout=30) as client:
        response = request_with_retries(
            client,
            "POST",
            TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "client_key": os.environ["TIKTOK_CLIENT_KEY"],
                "client_secret": os.environ["TIKTOK_CLIENT_SECRET"],
                "grant_type": "refresh_token",
                "refresh_token": os.environ["TIKTOK_REFRESH_TOKEN"],
            },
        )

    body = response.json()
    update_env_file(
        {
            "TIKTOK_ACCESS_TOKEN": body["access_token"],
            "TIKTOK_REFRESH_TOKEN": body["refresh_token"],
        }
    )
    return body["access_token"]


@task
def fetch_videos(access_token: str) -> list[dict]:
    videos = []
    cursor = None

    with httpx.Client(
        headers={"Authorization": f"Bearer {access_token}"}, timeout=30
    ) as client:
        while True:
            body = {"max_count": 20}
            if cursor is not None:
                body["cursor"] = cursor

            response = request_with_retries(
                client,
                "POST",
                VIDEO_LIST_URL,
                params={"fields": VIDEO_FIELDS},
                json=body,
            )
            data = response.json()["data"]
            videos.extend(data["videos"])
            print(f"Fetched {len(data['videos'])} videos (has_more={data['has_more']})")

            if not data["has_more"]:
                break
            cursor = data["cursor"]

    return videos


@task
def fetch_user_info(access_token: str) -> dict:
    with httpx.Client(
        headers={"Authorization": f"Bearer {access_token}"}, timeout=30
    ) as client:
        response = request_with_retries(
            client, "GET", USER_INFO_URL, params={"fields": USER_FIELDS}
        )
    return response.json()["data"]["user"]


@flow(name="tiktok-videos-ingestion")
def tiktok_videos_flow() -> None:
    access_token = refresh_access_token()

    videos = fetch_videos(access_token)
    print(f"Total videos fetched: {len(videos)}")
    save_raw_json(videos, "data/raw/tiktok_videos.json")
    load_raw_to_bigquery(videos, RAW_VIDEOS_TABLE_ID, tags={})

    user_info = fetch_user_info(access_token)
    print(f"User stats: {user_info}")
    save_raw_json([user_info], "data/raw/tiktok_user_info.json")
    load_raw_to_bigquery([user_info], RAW_USER_INFO_TABLE_ID, tags={})


if __name__ == "__main__":
    tiktok_videos_flow()
