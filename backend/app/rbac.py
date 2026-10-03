"""RBAC: roles × modules × permissions, loaded from `data/rbac.json`.

Architecture: each **module** groups a set of **actions**; a **permission** is
`"<module>.<action>"`. A **role** holds a set of permissions. The Access Control
admin page edits this matrix at runtime (persisted back to the JSON file).
"""
from __future__ import annotations

import json
import os
import threading

from fastapi import HTTPException

_DATA = os.path.join(os.path.dirname(__file__), "data", "rbac.json")
_LOCK = threading.Lock()
_CACHE: dict | None = None


def _load() -> dict:
    global _CACHE
    if _CACHE is None:
        with open(_DATA, encoding="utf-8") as fh:
            _CACHE = json.load(fh)
    return _CACHE


def _save(cfg: dict) -> None:
    global _CACHE
    with _LOCK:
        with open(_DATA, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, indent=2)
        _CACHE = cfg


def config() -> dict:
    return _load()


def modules() -> list[dict]:
    return _load()["modules"]


def roles() -> list[dict]:
    return _load()["roles"]


def role(role_id: str) -> dict | None:
    return next((r for r in roles() if r["id"] == role_id), None)


def valid_permissions() -> set[str]:
    out: set[str] = set()
    for m in modules():
        for a in m["actions"]:
            out.add(f"{m['id']}.{a['id']}")
    return out


def permissions_for_role(role_id: str) -> set[str]:
    r = role(role_id)
    return set(r["permissions"]) if r else set()


def role_has(role_id: str, permission: str) -> bool:
    return permission in permissions_for_role(role_id)


def set_role_permissions(role_id: str, permissions: list[str]) -> dict:
    cfg = json.loads(json.dumps(_load()))  # deep copy
    target = next((r for r in cfg["roles"] if r["id"] == role_id), None)
    if not target:
        raise HTTPException(status_code=404, detail=f"unknown role '{role_id}'")

    valid = valid_permissions()
    cleaned = sorted({p for p in permissions if p in valid})

    # Safety: a system role (platform_admin) must keep access_control.manage so
    # nobody can lock everyone out of the Access Control page.
    if target.get("system"):
        for must in ("access_control.view", "access_control.manage"):
            if must not in cleaned:
                cleaned.append(must)
        cleaned = sorted(set(cleaned))

    target["permissions"] = cleaned
    _save(cfg)
    return target
