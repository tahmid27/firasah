"""One-off check that MAILCHIMP_API_KEY authenticates against the
Mailchimp Marketing API. Also settles whether the Free plan actually
includes API access — ambiguous in Mailchimp's own docs, easiest to just
test directly.

Not part of the real ingestion pipeline — just proves auth works before
that gets built (Phase 3, Mailchimp/Klaviyo connector step).
"""

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ["MAILCHIMP_API_KEY"]
data_center = api_key.split("-")[-1]

# The API Root endpoint — simplest way to verify a key works and see what
# it can access.
response = httpx.get(
    f"https://{data_center}.api.mailchimp.com/3.0/",
    auth=("anystring", api_key),
)

print(f"Status: {response.status_code}")
print(response.json())
