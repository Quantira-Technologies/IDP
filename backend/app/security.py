"""Optional API-key authentication.

Kept intentionally simple for the POC: a single shared key toggled on via the
`API_KEY` setting. When no key is configured the dependency is a no-op so the
offline demo needs zero setup. Production would replace this with OIDC/JWT SSO
and per-tenant RBAC (see docs/PRODUCTIZATION.md).
"""
from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, status

from .config import settings


def require_api_key(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
) -> None:
    expected = settings.api_key
    if not expected:
        # Auth disabled — open API for local/offline demos.
        return

    presented = x_api_key
    if not presented and authorization and authorization.lower().startswith("bearer "):
        presented = authorization[7:].strip()

    # Constant-time comparison to avoid leaking the key via timing.
    if not presented or not hmac.compare_digest(presented, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing or invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
