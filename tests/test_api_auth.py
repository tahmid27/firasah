"""Auth and tenant resolution: a request only gets through with a genuine,
unexpired Supabase token, and the charity always comes from the server-side
membership lookup — never from anything the caller sends."""

import httpx
import pytest
from fastapi.testclient import TestClient

import main
from api.auth import CurrentUser, get_signing_keys
from api.settings import get_settings
from api.tenancy import SupabaseMembershipLookup, get_membership_lookup
from tests.api_helpers import (
    ATTACKER_KEY,
    SETTINGS,
    USER_A,
    USER_B,
    USER_NO_ORG,
    FakeMembershipLookup,
    FakeSigningKeys,
    bearer,
    hs256_confusion_token,
    token,
    unsigned_token,
)


@pytest.fixture
def lookup():
    return FakeMembershipLookup()


@pytest.fixture
def client(lookup):
    main.app.dependency_overrides = {
        get_settings: lambda: SETTINGS,
        get_signing_keys: lambda: FakeSigningKeys(),
        get_membership_lookup: lambda: lookup,
    }
    yield TestClient(main.app)
    main.app.dependency_overrides = {}


# --- the happy path ----------------------------------------------------------


def test_valid_token_resolves_the_users_own_charity(client):
    response = client.get("/me", headers=bearer(token(USER_A)))

    assert response.status_code == 200
    assert response.json() == {
        "user_id": USER_A,
        "org_id": "charity_a",
        "role": "admin",
    }


def test_two_users_get_their_own_charities(client):
    a = client.get("/me", headers=bearer(token(USER_A))).json()
    b = client.get("/me", headers=bearer(token(USER_B))).json()

    assert (a["org_id"], b["org_id"]) == ("charity_a", "charity_b")


# --- tokens that must be refused (401) ----------------------------------------


@pytest.mark.parametrize(
    ("description", "headers"),
    [
        ("no Authorization header", {}),
        ("not a bearer token", {"Authorization": "Basic dXNlcjpwYXNz"}),
        ("garbage token", bearer("not-a-jwt")),
        ("expired", bearer(token(exp=1_000_000_000))),
        ("signed by a key Supabase never published", bearer(token(key=ATTACKER_KEY))),
        ("alg:none — unsigned", bearer(unsigned_token())),
        ("HS256 signed with the public key", bearer(hs256_confusion_token())),
        ("wrong audience", bearer(token(aud="someone-else"))),
        ("wrong issuer", bearer(token(iss="https://evil.example/auth/v1"))),
        ("anon role, not a logged-in user", bearer(token(role="anon"))),
        ("no subject", bearer(token(sub=None))),
        ("subject is not a user id", bearer(token("charity_b"))),
        ("no expiry", bearer(token(exp=None))),
    ],
)
def test_bad_tokens_are_refused(client, lookup, description, headers):
    response = client.get("/me", headers=headers)

    assert response.status_code == 401, description
    assert response.headers.get("www-authenticate") == "Bearer"
    # Refused before any membership lookup happens
    assert lookup.calls == []


def test_refusals_never_explain_why(client):
    # Telling a caller why their token failed only helps someone forging one
    expired = client.get("/me", headers=bearer(token(exp=1_000_000_000)))
    forged = client.get("/me", headers=bearer(token(key=ATTACKER_KEY)))

    assert expired.json() == forged.json() == {"detail": "invalid token"}


# --- authenticated, but not authorised ---------------------------------------


def test_logged_in_user_with_no_charity_is_forbidden(client):
    response = client.get("/me", headers=bearer(token(USER_NO_ORG)))

    assert response.status_code == 403


def test_membership_service_down_is_a_503_not_a_leak(client):
    def broken(user):
        raise httpx.ConnectError("supabase unreachable")

    main.app.dependency_overrides[get_membership_lookup] = lambda: broken
    response = client.get("/me", headers=bearer(token(USER_A)))

    assert response.status_code == 503


# --- the charity can't be chosen by the caller --------------------------------


def test_org_id_in_the_request_is_ignored(client):
    # Every place a caller could try to smuggle another charity's ID in
    response = client.request(
        "GET",
        "/me",
        params={"org_id": "charity_b"},
        headers={**bearer(token(USER_A)), "X-Org-Id": "charity_b"},
        json={"org_id": "charity_b"},
    )

    assert response.status_code == 200
    assert response.json()["org_id"] == "charity_a"


def test_org_id_claims_inside_the_token_are_ignored(client):
    # Option A: the token proves WHO, the server decides WHICH charity —
    # even a validly signed token can't nominate its own org
    response = client.get(
        "/me",
        headers=bearer(
            token(USER_A, org_id="charity_b", app_metadata={"org_id": "charity_b"})
        ),
    )

    assert response.json()["org_id"] == "charity_a"


# --- the real Supabase lookup, against a fake transport ----------------------


def lookup_returning(status, rows, seen):
    def handler(request):
        seen.append(request)
        return httpx.Response(status, json=rows)

    return SupabaseMembershipLookup(
        SETTINGS, client=httpx.Client(transport=httpx.MockTransport(handler))
    )


def test_supabase_lookup_asks_as_the_user_not_as_the_service_role():
    seen = []
    lookup = lookup_returning(200, [{"org_id": "charity_a", "role": "admin"}], seen)

    result = lookup(CurrentUser(user_id=USER_A, token="users-own-jwt"))

    assert result == ("charity_a", "admin")
    request = seen[0]
    # The user's own token, so Supabase RLS limits the answer to their row
    assert request.headers["authorization"] == "Bearer users-own-jwt"
    assert request.headers["apikey"] == SETTINGS.supabase_anon_key
    assert request.url.params["user_id"] == f"eq.{USER_A}"


def test_supabase_lookup_no_row_means_no_charity():
    lookup = lookup_returning(200, [], [])

    assert lookup(CurrentUser(user_id=USER_A, token="t")) is None


def test_supabase_lookup_refuses_to_guess_between_two_memberships():
    rows = [{"org_id": "charity_a", "role": "admin"}, {"org_id": "x", "role": "member"}]
    lookup = lookup_returning(200, rows, [])

    with pytest.raises(RuntimeError):
        lookup(CurrentUser(user_id=USER_A, token="t"))


def test_supabase_lookup_errors_propagate():
    lookup = lookup_returning(500, {"message": "boom"}, [])

    with pytest.raises(httpx.HTTPStatusError):
        lookup(CurrentUser(user_id=USER_A, token="t"))
