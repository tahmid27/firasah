"""One-off check that JUSTGIVING_APP_ID authenticates against the staging API.

Not part of the real ingestion pipeline — just proves auth works before
that gets built (Phase 2, roadmap step 1).
"""

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

app_id = os.environ["JUSTGIVING_APP_ID"]

# charityId 2050 is JustGiving's documented example id for the staging environment
response = httpx.get(
    "https://api.staging.justgiving.com/v1/charity/2050",
    headers={"x-api-key": app_id, "Accept": "application/json"},
)

print(f"Status: {response.status_code}")
print(response.json())
