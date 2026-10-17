"""The one definition of what a valid tenant (charity) ID looks like.

Shared by ingestion (every BigQuery row is stamped with one), the API (every
request resolves to one) and the Supabase `organisations.id` check
constraint, which repeats the same pattern in SQL.
"""

import re

# Lowercase letters, digits, "_" and "-"; covers readable dev IDs like
# "test_charity" and generated UUIDs alike.
ORG_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")


def validate_org_id(org_id: str | None) -> str:
    """Returns org_id if it is a well-formed tenant ID, otherwise raises.
    A missing or malformed org_id is always a hard error — never a default,
    because a default would silently assign data to some charity."""
    if not isinstance(org_id, str) or not ORG_ID_PATTERN.match(org_id):
        raise ValueError(f"invalid or missing org_id: {org_id!r}")
    return org_id
