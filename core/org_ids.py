"""Tenant ID format, shared by ingestion, the API and the Supabase check constraint."""

import re

# Covers readable IDs like "test_charity" and UUIDs
ORG_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")


def validate_org_id(org_id: str | None) -> str:
    """Returns org_id if well-formed, otherwise raises ValueError."""
    if not isinstance(org_id, str) or not ORG_ID_PATTERN.match(org_id):
        raise ValueError(f"invalid or missing org_id: {org_id!r}")
    return org_id
