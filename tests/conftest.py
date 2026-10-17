"""Shared pytest setup.

Some connectors read API keys from the environment the moment they're
imported (e.g. `APP_ID = os.environ["JUSTGIVING_APP_ID"]`). CI has no .env
file, so dummy values are set here before any test imports them. These are
never sent anywhere: the tests only exercise pure functions and a fake HTTP
transport, never a real API. `setdefault` leaves a real local .env alone.
"""

import os

for key in (
    "JUSTGIVING_APP_ID",
    "MAILCHIMP_API_KEY",
    "INSTAGRAM_ACCESS_TOKEN",
    "TIKTOK_CLIENT_KEY",
    "TIKTOK_CLIENT_SECRET",
    "TIKTOK_REFRESH_TOKEN",
):
    os.environ.setdefault(key, "test-dummy-value-us1")
