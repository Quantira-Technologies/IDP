"""Authentication: password login, provisioned SSO, and HMAC-signed tokens.

Kept dependency-free (stdlib only). Tokens are compact `payload.signature`
strings signed with the app secret — good enough for the POC and trivial to
swap for real OIDC/JWT later. Synthetic users live in `data/users.json`.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from functools import lru_cache

from fastapi import Depends, Header, HTTPException, status

from .config import settings
from . import rbac

_DATA = os.path.join(os.path.dirname(__file__), "data", "users.json")


@lru_cache(maxsize=1)
def _users() -> list[dict]:
    with open(_DATA, encoding="utf-8") as fh:
        return json.load(fh)["users"]


def _find_user(username: str) -> dict | None:
    uname = (username or "").strip().lower()
    for u in _users():
        if u["username"].lower() == uname:
            return u
    return None


def hash_password(username: str, password: str) -> str:
    return hashlib.sha256(f"{settings.auth_secret}:{username}:{password}".encode()).hexdigest()


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64d(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def make_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": int(time.time()) + settings.token_ttl}
    body = _b64e(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(settings.auth_secret.encode(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64e(sig)}"


def verify_token(token: str) -> dict | None:
    try:
        body, sig = token.split(".", 1)
    except ValueError:
        return None
    expected = _b64e(hmac.new(settings.auth_secret.encode(), body.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        payload = json.loads(_b64d(body))
    except (ValueError, json.JSONDecodeError):
        return None
    if payload.get("exp", 0) < int(time.time()):
        return None
    return payload


def public_user(user: dict) -> dict:
    """User shape returned to the client — never includes the password hash."""
    perms = rbac.permissions_for_role(user["role"])
    role = rbac.role(user["role"])
    return {
        "id": user["id"],
        "username": user["username"],
        "name": user["name"],
        "title": user.get("title", ""),
        "email": user.get("email", ""),
        "role": user["role"],
        "role_label": role["label"] if role else user["role"],
        "permissions": sorted(perms),
    }


def authenticate(username: str, password: str) -> dict:
    user = _find_user(username)
    if not user or not hmac.compare_digest(
        user["password_hash"], hash_password(user["username"], password)
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    return user


def sso_user(role_hint: str | None = None) -> dict:
    """Provisioned SSO sign-in — resolves to a demo user (role-selectable).

    In production this is replaced by an OIDC callback (Nafath / Azure AD) that
    maps the federated identity + group claims to a role.
    """
    target = role_hint or "customs_officer"
    for u in _users():
        if u["role"] == target:
            return u
    return _users()[0]


# --------------------------------------------------------------------------- #
# FastAPI dependencies
# --------------------------------------------------------------------------- #
def _user_from_header(authorization: str | None) -> dict | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    payload = verify_token(authorization[7:].strip())
    if not payload:
        return None
    for u in _users():
        if u["id"] == payload.get("sub"):
            return u
    return None


def current_user(authorization: str | None = Header(default=None)) -> dict:
    if not settings.auth_enabled:
        # Auth disabled (e.g. tests) — act as the admin so everything is allowed.
        return _users()[0]
    user = _user_from_header(authorization)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_permission(permission: str):
    """Dependency factory: require the caller's role to hold `permission`."""

    def _dep(user: dict = Depends(current_user)) -> dict:
        if not settings.auth_enabled:
            return user
        if not rbac.role_has(user["role"], permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"missing permission: {permission}",
            )
        return user

    return _dep
