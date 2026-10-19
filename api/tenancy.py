"""Resolves the caller's organisation from Supabase memberships on each request."""

from dataclasses import dataclass
from typing import Annotated, Protocol

import httpx
from fastapi import Depends, HTTPException, status

from api.auth import CurrentUser, get_current_user
from api.settings import Settings, get_settings
from core.org_ids import validate_org_id


@dataclass(frozen=True)
class OrgContext:
    """The verified identity tenant-scoped endpoints work from."""

    user_id: str
    org_id: str
    role: str
    org_name: str | None = None


class MembershipLookup(Protocol):
    def __call__(self, user: CurrentUser) -> tuple[str, str, str | None] | None:
        """(org_id, role, organisation name) for this user, or None if they belong to none."""


class SupabaseMembershipLookup:
    """Reads the caller's membership with their own token (not the service
    role), so Supabase RLS applies."""

    def __init__(self, settings: Settings, client: httpx.Client | None = None):
        self._settings = settings
        self._client = client or httpx.Client(timeout=10)

    def __call__(self, user: CurrentUser) -> tuple[str, str, str | None] | None:
        request = {
            "params": {
                "select": "org_id,role,organisations(name)",
                "user_id": f"eq.{user.user_id}",
            },
            "headers": {
                "apikey": self._settings.supabase_anon_key,
                "Authorization": f"Bearer {user.token}",
            },
        }
        url = f"{self._settings.supabase_url}/rest/v1/memberships"
        try:
            response = self._client.get(url, **request)
        except httpx.TransportError:
            # A pooled connection the server closed while idle fails on first
            # use; a read is safe to repeat, so try once more on a fresh one
            response = self._client.get(url, **request)
        response.raise_for_status()
        rows = response.json()
        if not rows:
            return None
        if len(rows) > 1:
            # memberships.user_id is the primary key, so this shouldn't happen
            raise RuntimeError("user has more than one membership")
        organisation = rows[0].get("organisations") or {}
        return rows[0]["org_id"], rows[0]["role"], organisation.get("name")


_lookups: dict[str, SupabaseMembershipLookup] = {}


def get_membership_lookup(
    settings: Annotated[Settings, Depends(get_settings)],
) -> MembershipLookup:
    # One reusable HTTP client per Supabase project, not one per request
    if settings.supabase_url not in _lookups:
        _lookups[settings.supabase_url] = SupabaseMembershipLookup(settings)
    return _lookups[settings.supabase_url]


def get_org_context(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    lookup: Annotated[MembershipLookup, Depends(get_membership_lookup)],
) -> OrgContext:
    try:
        membership = lookup(user)
    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="membership service unavailable",
        ) from None

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="no organisation for this user",
        )

    org_id, role, org_name = membership
    return OrgContext(
        user_id=user.user_id,
        org_id=validate_org_id(org_id),
        role=role,
        org_name=org_name,
    )


# Endpoints declare `ctx: CurrentOrg`
CurrentOrg = Annotated[OrgContext, Depends(get_org_context)]
