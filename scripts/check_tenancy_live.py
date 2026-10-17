"""Live tenancy check against the real Supabase project: RLS, then the API.

Creates a temporary second organisation and user, runs the checks, then
deletes them. Needs the FIRASAH_TEST_* users in .env.

Usage: uv run python -m scripts.check_tenancy_live
"""

import base64
import json
import os
import secrets
import sys

import httpx
from dotenv import load_dotenv
from fastapi.testclient import TestClient

import main

load_dotenv(".env")

URL = os.environ["SUPABASE_URL"].rstrip("/")
ANON = os.environ["SUPABASE_ANON_KEY"]
SERVICE = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
TEMP_ORG = "rls_test_org"
TEMP_EMAIL = "rls-temp-user@example.com"

results: list[bool] = []


def check(label: str, ok: bool, detail="") -> None:
    results.append(ok)
    print(("PASS " if ok else "FAIL ") + label + (f"  [{detail}]" if not ok else ""))


def headers(key: str, **extra) -> dict:
    return {
        "apikey": SERVICE if key == SERVICE else ANON,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
        **extra,
    }


def rest(method: str, path: str, key: str, **kwargs) -> httpx.Response:
    extra = kwargs.pop("extra_headers", {})
    return httpx.request(
        method, f"{URL}/rest/v1/{path}", headers=headers(key, **extra), **kwargs
    )


def sign_in(email: str, password: str) -> str:
    response = httpx.post(
        f"{URL}/auth/v1/token?grant_type=password",
        headers={"apikey": ANON},
        json={"email": email, "password": password},
    )
    response.raise_for_status()
    return response.json()["access_token"]


def forge_subject(token: str, new_sub: str) -> str:
    """The caller's real token with its user ID edited, signature unchanged."""
    head, payload, signature = token.split(".")
    claims = json.loads(base64.urlsafe_b64decode(payload + "=="))
    claims["sub"] = new_sub
    edited = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=")
    return f"{head}.{edited.decode()}.{signature}"


def setup() -> tuple[str, str]:
    member_id = os.environ["FIRASAH_TEST_MEMBER_USER_ID"]
    r = rest("GET", "organisations", SERVICE)
    check(
        "service role can read organisations",
        r.status_code == 200 and any(o["id"] == "test_charity" for o in r.json()),
        r.text[:150],
    )
    r = rest(
        "POST",
        "memberships?on_conflict=user_id",
        SERVICE,
        json={"user_id": member_id, "org_id": "test_charity", "role": "admin"},
        extra_headers={"Prefer": "resolution=merge-duplicates,return=representation"},
    )
    check(
        "test member linked to test_charity", r.status_code in (200, 201), r.text[:150]
    )

    rest(
        "POST", "organisations", SERVICE, json={"id": TEMP_ORG, "name": "RLS Test Org"}
    )
    password = secrets.token_urlsafe(24)
    r = httpx.post(
        f"{URL}/auth/v1/admin/users",
        headers=headers(SERVICE),
        json={"email": TEMP_EMAIL, "password": password, "email_confirm": True},
    )
    temp_user_id = r.json()["id"]
    rest(
        "POST",
        "memberships",
        SERVICE,
        json={"user_id": temp_user_id, "org_id": TEMP_ORG, "role": "member"},
    )
    return temp_user_id, password


def check_rls(member: str, no_org: str, temp: str, temp_user_id: str) -> None:
    member_id = os.environ["FIRASAH_TEST_MEMBER_USER_ID"]
    no_org_id = os.environ["FIRASAH_TEST_NO_ORG_USER_ID"]

    r = rest("GET", "memberships", member)
    check(
        "member sees exactly their own membership row",
        r.status_code == 200 and [m["user_id"] for m in r.json()] == [member_id],
        r.text[:150],
    )
    r = rest("GET", "organisations", member)
    check(
        "member sees only test_charity", [o["id"] for o in r.json()] == ["test_charity"]
    )
    r = rest("GET", f"organisations?id=eq.{TEMP_ORG}", member)
    check("member asking for the other org by ID gets nothing", r.json() == [])
    r = rest("GET", f"memberships?user_id=eq.{temp_user_id}", member)
    check("member asking for another user's membership gets nothing", r.json() == [])
    r = rest("GET", "organisations", temp)
    check(
        "second org's user sees only their org",
        [o["id"] for o in r.json()] == [TEMP_ORG],
    )
    r = rest("GET", "memberships", no_org)
    check("user with no charity sees no memberships", r.json() == [])

    r = rest(
        "POST",
        "memberships",
        no_org,
        json={"user_id": no_org_id, "org_id": "test_charity", "role": "admin"},
    )
    check("user can't add themselves to a charity", r.status_code >= 400, r.status_code)
    r = rest(
        "PATCH",
        f"memberships?user_id=eq.{member_id}",
        member,
        json={"org_id": TEMP_ORG},
    )
    check(
        "member can't move to another charity", r.status_code >= 400 or r.json() == []
    )
    r = rest(
        "PATCH", "organisations?id=eq.test_charity", member, json={"name": "hijacked"}
    )
    check("member can't rename their charity", r.status_code >= 400 or r.json() == [])
    r = rest("DELETE", f"memberships?user_id=eq.{temp_user_id}", member)
    check(
        "member can't delete another user's membership",
        r.status_code >= 400 or r.json() == [],
    )
    still = rest("GET", f"memberships?user_id=eq.{temp_user_id}", SERVICE).json()
    check("...and that membership still exists", len(still) == 1)

    for table in ("organisations", "memberships"):
        r = rest("GET", table, ANON)
        check(
            f"anon key refused on {table}", r.status_code in (401, 403), r.status_code
        )


def check_api(member: str, no_org: str, temp: str, temp_user_id: str) -> None:
    main.app.dependency_overrides = {}
    api = TestClient(main.app)

    def me(token, **kwargs):
        headers = {"Authorization": f"Bearer {token}", **kwargs.pop("headers", {})}
        return api.get("/me", headers=headers, **kwargs)

    r = me(member)
    check(
        "API: member resolves to test_charity",
        r.status_code == 200
        and r.json()["org_id"] == "test_charity"
        and r.json()["user_id"] == os.environ["FIRASAH_TEST_MEMBER_USER_ID"],
        r.text[:150],
    )
    r = me(temp)
    check(
        "API: second org's user resolves to their org",
        r.json().get("org_id") == TEMP_ORG,
    )
    check("API: user with no charity gets 403", me(no_org).status_code == 403)
    check("API: anon key as a token gets 401", me(ANON).status_code == 401)
    check("API: service-role key as a token gets 401", me(SERVICE).status_code == 401)
    forged = forge_subject(member, temp_user_id)
    check(
        "API: real token edited to claim another user gets 401",
        me(forged).status_code == 401,
    )
    r = me(member, params={"org_id": TEMP_ORG}, headers={"X-Org-Id": TEMP_ORG})
    check("API: smuggled org_id is ignored", r.json().get("org_id") == "test_charity")


def cleanup(temp_user_id: str | None) -> None:
    if temp_user_id:
        httpx.delete(
            f"{URL}/auth/v1/admin/users/{temp_user_id}", headers=headers(SERVICE)
        )
    rest("DELETE", f"organisations?id=eq.{TEMP_ORG}", SERVICE)
    orgs = [o["id"] for o in rest("GET", "organisations", SERVICE).json()]
    print(f"cleanup: organisations now {orgs}")


def run() -> int:
    temp_user_id = None
    try:
        temp_user_id, temp_password = setup()
        member = sign_in(
            os.environ["FIRASAH_TEST_MEMBER_EMAIL"],
            os.environ["FIRASAH_TEST_MEMBER_PASSWORD"],
        )
        no_org = sign_in(
            os.environ["FIRASAH_TEST_NO_ORG_EMAIL"],
            os.environ["FIRASAH_TEST_NO_ORG_PASSWORD"],
        )
        temp = sign_in(TEMP_EMAIL, temp_password)
        check_rls(member, no_org, temp, temp_user_id)
        check_api(member, no_org, temp, temp_user_id)
    finally:
        cleanup(temp_user_id)
    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(run())
