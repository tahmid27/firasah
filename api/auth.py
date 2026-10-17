"""Verifies the Supabase JWT on each request."""

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

# auto_error=False so a missing header gets our 401 instead of FastAPI's 403
_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    user_id: str
    token: str  # forwarded to the membership lookup so Supabase RLS applies


class SigningKeys:
    """Supabase's published signing keys (JWKS), cached."""

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
        raise _unauthorized("invalid token") from None

    if claims.get("role") != "authenticated":
        raise _unauthorized("invalid token")
    try:
        user_id = str(uuid.UUID(claims["sub"]))
    except ValueError:
        raise _unauthorized("invalid token") from None

    return CurrentUser(user_id=user_id, token=token)
