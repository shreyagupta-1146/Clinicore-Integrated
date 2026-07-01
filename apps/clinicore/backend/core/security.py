"""
apps/clinicore/backend/core/security.py

Keycloak-backed authentication. Verifies RS256 JWTs against the realm's
published JWKS (fetched once, cached, refreshed on kid-miss). Replaces
Auth0 per the integration plan — Keycloak gives us self-hosted identity
(India data-residency requirement) plus native FIDO2/WebAuthn support.

Step-up MFA: clinicians unlocking a step-up-protected folder must present
a token whose `acr` claim matches the realm's configured high-assurance
level (see infrastructure/keycloak/realm-export.json — "fido2-required" flow).
This module only verifies the claim is present; the Keycloak authentication
flow is what actually enforces the FIDO2 challenge before issuing it.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from apps.clinicore.backend.core.config import ClinicoreSettings, get_settings

_bearer_scheme = HTTPBearer(auto_error=True)

_STEP_UP_ACR = "fido2-required"


@dataclass
class AuthenticatedUser:
    user_id: str
    email: Optional[str]
    roles: List[str]
    clinic_id: Optional[str]
    acr: Optional[str]
    raw_claims: Dict[str, Any]

    @property
    def is_clinician(self) -> bool:
        return "clinician" in self.roles

    @property
    def is_clinic_admin(self) -> bool:
        return "clinic_admin" in self.roles

    @property
    def has_step_up(self) -> bool:
        return self.acr == _STEP_UP_ACR


class _JWKSCache:
    """Caches the realm's JWKS document; refetches on TTL expiry or kid-miss."""

    def __init__(self, jwks_url: str, ttl_seconds: int = 3600):
        self._jwks_url = jwks_url
        self._ttl = ttl_seconds
        self._keys: Dict[str, Dict[str, Any]] = {}
        self._fetched_at: float = 0.0

    async def get_key(self, kid: str) -> Optional[Dict[str, Any]]:
        if kid not in self._keys or (time.monotonic() - self._fetched_at) > self._ttl:
            await self._refresh()
        return self._keys.get(kid)

    async def _refresh(self) -> None:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            resp = await client.get(self._jwks_url)
            resp.raise_for_status()
            jwks = resp.json()
        self._keys = {k["kid"]: k for k in jwks.get("keys", [])}
        self._fetched_at = time.monotonic()


_jwks_cache_singleton: Optional[_JWKSCache] = None


def _get_jwks_cache(settings: ClinicoreSettings) -> _JWKSCache:
    global _jwks_cache_singleton
    if _jwks_cache_singleton is None:
        jwks_url = (
            f"{settings.keycloak_url}/realms/{settings.keycloak_realm}"
            "/protocol/openid-connect/certs"
        )
        _jwks_cache_singleton = _JWKSCache(jwks_url)
    return _jwks_cache_singleton


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    settings: ClinicoreSettings = Depends(get_settings),
) -> AuthenticatedUser:
    token = credentials.credentials
    cache = _get_jwks_cache(settings)

    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Malformed token") from exc

    kid = unverified_header.get("kid")
    jwk = await cache.get_key(kid) if kid else None
    if jwk is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown signing key")

    issuer = f"{settings.keycloak_url}/realms/{settings.keycloak_realm}"
    try:
        claims = jwt.decode(
            token,
            jwk,
            algorithms=["RS256"],
            audience=settings.keycloak_clinicore_client_id,
            issuer=issuer,
        )
    except JWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {exc}") from exc

    realm_access = claims.get("realm_access", {})
    roles = realm_access.get("roles", [])

    return AuthenticatedUser(
        user_id=claims["sub"],
        email=claims.get("email"),
        roles=roles,
        clinic_id=claims.get("clinic_id"),
        acr=claims.get("acr"),
        raw_claims=claims,
    )


def require_clinician(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    if not user.is_clinician:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Clinician role required")
    return user


def require_step_up(user: AuthenticatedUser = Depends(require_clinician)) -> AuthenticatedUser:
    if not user.has_step_up:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "This action requires step-up authentication (FIDO2). "
            "Re-authenticate via the high-assurance login flow.",
        )
    return user
