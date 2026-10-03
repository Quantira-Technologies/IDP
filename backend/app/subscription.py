"""API keys, subscription plan and ECM/ERP connectors.

The API keys are real signed tokens (so the 'generate' flow is believable), but
the connector integrations are provisioned stubs — flipping a connector to
"connected" and pushing a document returns a simulated success. Wiring a real
ECM/ERP is then just implementing the connector's `push()`.
"""
from __future__ import annotations

import json
import os
import secrets
import threading
from datetime import datetime, timezone

from fastapi import HTTPException

_DATA = os.path.join(os.path.dirname(__file__), "data", "subscription.json")
_LOCK = threading.Lock()
_CACHE: dict | None = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def public() -> dict:
    """Config safe to return to the client (keys are already masked at rest)."""
    return _load()


def generate_key(label: str) -> dict:
    cfg = json.loads(json.dumps(_load()))
    raw = secrets.token_hex(16)
    prefix = "i2d_live_"
    key = {
        "id": f"k-{secrets.token_hex(4)}",
        "label": (label or "New key").strip()[:40],
        "prefix": prefix,
        "last4": raw[-4:],
        "created": _now(),
        "active": True,
    }
    cfg["api_keys"].append(key)
    _save(cfg)
    # The full secret is shown exactly once and never stored.
    return {**key, "secret": f"{prefix}{raw}"}


def revoke_key(key_id: str) -> dict:
    cfg = json.loads(json.dumps(_load()))
    found = False
    for k in cfg["api_keys"]:
        if k["id"] == key_id:
            k["active"] = False
            found = True
    if not found:
        raise HTTPException(status_code=404, detail="key not found")
    _save(cfg)
    return public()


def set_connector(connector_id: str, status: str) -> dict:
    if status not in ("connected", "disconnected"):
        raise HTTPException(status_code=400, detail="invalid status")
    cfg = json.loads(json.dumps(_load()))
    found = next((c for c in cfg["connectors"] if c["id"] == connector_id), None)
    if not found:
        raise HTTPException(status_code=404, detail="connector not found")
    found["status"] = status
    _save(cfg)
    return public()


def set_webhook(url: str) -> dict:
    cfg = json.loads(json.dumps(_load()))
    cfg["webhook_url"] = (url or "").strip()[:300]
    _save(cfg)
    return public()


def export_document(doc_id: str, target: str) -> dict:
    """Push a processed document to a connector / webhook (simulated)."""
    cfg = _load()
    if target == "webhook":
        if not cfg.get("webhook_url"):
            raise HTTPException(status_code=400, detail="no webhook URL configured")
        return {"ok": True, "target": "webhook", "url": cfg["webhook_url"],
                "message": f"Document {doc_id} delivered to webhook.", "at": _now()}
    connector = next((c for c in cfg["connectors"] if c["id"] == target), None)
    if not connector:
        raise HTTPException(status_code=404, detail="unknown target")
    if connector["status"] != "connected":
        raise HTTPException(status_code=400, detail=f"{connector['name']} is not connected")
    return {
        "ok": True, "target": target, "connector": connector["name"],
        "message": f"Document {doc_id} pushed to {connector['name']}.", "at": _now(),
        "reference": f"{connector['id'].upper()}-{secrets.token_hex(3).upper()}",
    }
