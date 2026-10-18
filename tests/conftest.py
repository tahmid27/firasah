"""Dummy API keys, for connectors that read them at import time (CI has no .env)."""

import os

for key in (
    "JUSTGIVING_APP_ID",
    "MAILCHIMP_API_KEY",
    "INSTAGRAM_ACCESS_TOKEN",
    "TIKTOK_CLIENT_KEY",
    "TIKTOK_CLIENT_SECRET",
    "TIKTOK_REFRESH_TOKEN",
    "GOOGLE_CLOUD_PROJECT",
):
    os.environ.setdefault(key, "test-dummy-value-us1")
