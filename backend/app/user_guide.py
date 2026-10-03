"""Role-aware in-app user guide.

Each section can require a permission; a user only sees sections they have access
to. Tenant/platform admins can edit section titles and bodies.
"""
from __future__ import annotations

import json
import os
import threading

from fastapi import HTTPException

_DATA = os.path.join(os.path.dirname(__file__), "data", "user_guide.json")
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


def sections_for(permissions: set[str]) -> list[dict]:
    out = []
    for s in _load()["sections"]:
        perm = s.get("permission")
        if perm is None or perm in permissions:
            out.append(s)
    return out


def all_sections() -> list[dict]:
    return _load()["sections"]


def update_section(section_id: str, title: str | None, body: str | None) -> dict:
    cfg = json.loads(json.dumps(_load()))
    target = next((s for s in cfg["sections"] if s["id"] == section_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="section not found")
    if title is not None:
        target["title"] = title.strip()[:120] or target["title"]
    if body is not None:
        target["body"] = body.strip()[:4000]
    _save(cfg)
    return target
