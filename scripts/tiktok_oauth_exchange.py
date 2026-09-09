"""One-off exchange of a TikTok authorization code for an access token.

Not part of the real ingestion pipeline. TikTok's OAuth flow needs a human
to log in and authorize in a browser first (build the authorize URL with
TIKTOK_CLIENT_KEY, open it, log in as the target account) — that produces
a short-lived, single-use `code` in the redirect. This script trades that
code for the access_token + refresh_token the real connector needs.

Usage: uv run python scripts/tiktok_oauth_exchange.py <code>
"""

import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

REDIRECT_URI = "https://your-ngrok-static-domain.ngrok-free.dev/auth/tiktok/callback"

code = sys.argv[1]

response = httpx.post(
    "https://open.tiktokapis.com/v2/oauth/token/",
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    data={
        "client_key": os.environ["TIKTOK_CLIENT_KEY"],
        "client_secret": os.environ["TIKTOK_CLIENT_SECRET"],
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    },
)

print(f"Status: {response.status_code}")
body = response.json()
print(body)

if "access_token" in body:
    print("\nAdd these to .env:")
    print(f"TIKTOK_ACCESS_TOKEN={body['access_token']}")
    print(f"TIKTOK_REFRESH_TOKEN={body['refresh_token']}")
