"""One-off exchange of a short-lived Instagram/Facebook Page access token
for Meta's long-lived (60-day) version.

Not part of the real ingestion pipeline — run manually whenever the token
needs refreshing. Unlike TikTok's refresh token (which rotates and gets
reissued on every real connector run), Meta's long-lived Page token is a
one-time upgrade from the short-lived token Graph API Explorer hands out,
not something traded on every pipeline run.

Usage: uv run python scripts/instagram_token_exchange.py
"""

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

response = httpx.get(
    "https://graph.facebook.com/v26.0/oauth/access_token",
    params={
        "grant_type": "fb_exchange_token",
        "client_id": os.environ["INSTAGRAM_APP_ID"],
        "client_secret": os.environ["INSTAGRAM_APP_SECRET"],
        "fb_exchange_token": os.environ["INSTAGRAM_ACCESS_TOKEN"],
    },
)

print(f"Status: {response.status_code}")
body = response.json()
print(body)

if "access_token" in body:
    print("\nAdd this to .env:")
    print(f"INSTAGRAM_ACCESS_TOKEN={body['access_token']}")
