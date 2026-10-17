"""Shared fixtures for API tests: test settings, a test signing key, a token
factory (including deliberately malicious tokens), and a fake membership
table. Nothing here talks to Supabase or BigQuery."""

import base64
import hashlib
import hmac
import json
import time
import uuid

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from api.settings import Settings

SETTINGS = Settings(
    supabase_url="https://test-project.supabase.co",
    supabase_anon_key="anon-test-key",
    bigquery_project="test-project",
    bigquery_dataset="test_dataset",
)

# Supabase's real key would be fetched from its JWKS URL; tests make their
# own, plus a second "attacker" key that Supabase never published.
SIGNING_KEY = ec.generate_private_key(ec.SECP256R1())
ATTACKER_KEY = ec.generate_private_key(ec.SECP256R1())
PUBLIC_PEM = SIGNING_KEY.public_key().public_bytes(
    serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
)

USER_A = str(uuid.uuid4())  # member of charity_a
USER_B = str(uuid.uuid4())  # member of charity_b
USER_NO_ORG = str(uuid.uuid4())  # logged in, but in no charity

MEMBERSHIPS = {
    USER_A: ("charity_a", "admin"),
    USER_B: ("charity_b", "member"),
}


class FakeSigningKeys:
    """Always hands back the genuine public key — so a token signed with
    anything else fails verification, exactly as with Supabase's JWKS."""

    def key_for(self, token):
        return SIGNING_KEY.public_key()


class FakeMembershipLookup:
    def __init__(self, memberships=MEMBERSHIPS):
        self.memberships = memberships
        self.calls = []

    def __call__(self, user):
        self.calls.append(user)
        return self.memberships.get(user.user_id)


def claims(user_id=USER_A, **overrides):
    now = int(time.time())
    base = {
        "sub": user_id,
        "aud": "authenticated",
        "role": "authenticated",
        "iss": f"{SETTINGS.supabase_url}/auth/v1",
        "iat": now,
        "exp": now + 3600,
    }
    base.update(overrides)
    return {k: v for k, v in base.items() if v is not None}


def token(user_id=USER_A, key=SIGNING_KEY, **overrides):
    return jwt.encode(
        claims(user_id, **overrides), key, algorithm="ES256", headers={"kid": "test"}
    )


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def raw_token(header: dict, payload: dict, signature: bytes = b"") -> str:
    """Hand-builds a JWT, for attacks a normal JWT library refuses to make."""
    head = _b64(json.dumps(header).encode())
    body = _b64(json.dumps(payload).encode())
    return f"{head}.{body}.{_b64(signature)}"


def unsigned_token(user_id=USER_A) -> str:
    """The `alg: none` attack: a token that claims it needs no signature."""
    return raw_token({"alg": "none", "typ": "JWT"}, claims(user_id))


def hs256_confusion_token(user_id=USER_A) -> str:
    """The algorithm-confusion attack: an HS256 token whose HMAC "secret" is
    the server's PUBLIC key (which anyone can download). A server that
    trusted the token's own `alg` header would accept it."""
    header = {"alg": "HS256", "typ": "JWT", "kid": "test"}
    head = _b64(json.dumps(header).encode())
    body = _b64(json.dumps(claims(user_id)).encode())
    signature = hmac.new(PUBLIC_PEM, f"{head}.{body}".encode(), hashlib.sha256)
    return f"{head}.{body}.{_b64(signature.digest())}"


def bearer(value: str) -> dict:
    return {"Authorization": f"Bearer {value}"}
