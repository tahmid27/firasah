"""Who is calling? Verifies the Supabase login token on every request.

When someone logs in, Supabase gives their browser a JWT: a small signed
statement ("this is user X, valid until 3pm"). The browser sends it on every
request as `Authorization: Bearer <token>`. Verifying it means checking:

  * the signature, with Supabase's PUBLIC key (fetched from its JWKS URL) —
    so the API never holds a secret that could forge tokens;
  * the algorithm is exactly ES256 — an explicit allowlist, which blocks the
    classic attacks where a forged token claims `alg: none` (unsigned) or
    `HS256` signed with the public key as if it were a password;
  * it hasn't expired, was issued by THIS Supabase project, and is meant for
    logged-in users (audience "authenticated", role "authenticated").

Anything else is a 401. The result is only "who" — which charity they
belong to is decided separately, server-side (see api/tenancy.py).
"""

import uuid
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.settings import Settings, get_settings

ALLOWED_ALGORITHMS = ["ES256"]
AUDIENCE = "authenticated"

# auto_error=False: we raise our own 401 (with the right header) instead of
# FastAPI's default 403 for a missing header.
_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    user_id: str
    # Kept so the membership lookup can be made AS this user, letting
    # Supabase's RLS limit the answer to their own row.
    token: str


class SigningKeys:
    """Finds the public key that matches a token's key ID, using Supabase's
    published JWKS. Keys are cached, so this isn't a network call per
    request. Wrapped in a class so tests can substitute their own keys."""

    def __init__(self, jwks_url: str):
        self._client = jwt.PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)

    def key_for(self, token: str):
        return self._client.get_signing_key_from_jwt(token).key


@lru_cache
def _signing_keys_for(jwks_url: str) -> SigningKeys:
    return SigningKeys(jwks_url)


def get_signing_keys(
    settings: Annotated[Settings, Depends(get_settings)],
) -> SigningKeys:
    return _signing_keys_for(settings.jwks_url)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
    keys: Annotated[SigningKeys, Depends(get_signing_keys)],
) -> CurrentUser:
    if credentials is None:
        raise _unauthorized("missing bearer token")
    token = credentials.credentials

    try:
        claims = jwt.decode(
            token,
            keys.key_for(token),
            algorithms=ALLOWED_ALGORITHMS,
            audience=AUDIENCE,
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "sub", "aud", "iss"]},
        )
    except jwt.PyJWTError:
        # One generic message for every failure: telling a caller *why*
        # their token was rejected only helps someone forging one.
        raise _unauthorized("invalid token") from None

    if claims.get("role") != "authenticated":
        raise _unauthorized("invalid token")
    try:
        user_id = str(uuid.UUID(claims["sub"]))
    except ValueError:
        raise _unauthorized("invalid token") from None

    return CurrentUser(user_id=user_id, token=token)
