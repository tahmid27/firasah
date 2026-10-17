"""Which charity is the caller acting for? Resolved server-side, every time.

Option A (decided 2026-10-17): the login token only proves WHO the caller
is; their charity is looked up in Supabase's `memberships` table on each
request. Removing someone from a charity therefore takes effect on their
very next request — nothing stale lives in the token.

The org_id NEVER comes from the request itself (URL, query string, body or
headers): anything there can be typed by an attacker. Endpoints get it only
from the OrgContext this module produces.
"""

from dataclasses import dataclass
from typing import Annotated, Protocol

import httpx
from fastapi import Depends, HTTPException, status

from api.auth import CurrentUser, get_current_user
from api.settings import Settings, get_settings
from core.org_ids import validate_org_id


@dataclass(frozen=True)
class OrgContext:
    """The verified identity every tenant-scoped endpoint works from."""

    user_id: str
    org_id: str
    role: str


class MembershipLookup(Protocol):
    def __call__(self, user: CurrentUser) -> tuple[str, str] | None:
        """(org_id, role) for this user, or None if they belong to none."""


class SupabaseMembershipLookup:
    """Reads the caller's membership row through Supabase's REST API, *as
    the caller*: it sends the user's own token, not the service-role key.

    That means Supabase's RLS policy ("users read their own membership")
    applies, so even if this code had a bug the database would still only
    return the caller's own row. The API never needs the RLS-bypassing
    service-role key for this — least privilege.
    """

    def __init__(self, settings: Settings, client: httpx.Client | None = None):
        self._settings = settings
        self._client = client or httpx.Client(timeout=10)

    def __call__(self, user: CurrentUser) -> tuple[str, str] | None:
        response = self._client.get(
            f"{self._settings.supabase_url}/rest/v1/memberships",
            params={"select": "org_id,role", "user_id": f"eq.{user.user_id}"},
            headers={
                "apikey": self._settings.supabase_anon_key,
                "Authorization": f"Bearer {user.token}",
            },
        )
        response.raise_for_status()
        rows = response.json()
        if not rows:
            return None
        if len(rows) > 1:
            # Impossible while memberships.user_id is the primary key (one
            # charity per user); refuse rather than guess if that changes.
            raise RuntimeError("user has more than one membership")
        return rows[0]["org_id"], rows[0]["role"]


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
        # Logged in, but not a member of any charity: authenticated, yet
        # not authorised to see any tenant's data.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="no organisation for this user",
        )

    org_id, role = membership
    return OrgContext(user_id=user.user_id, org_id=validate_org_id(org_id), role=role)


# What endpoints declare: `def endpoint(ctx: CurrentOrg)`. The route-coverage
# test checks every non-public route depends on get_org_context.
CurrentOrg = Annotated[OrgContext, Depends(get_org_context)]
