"""Business-rule / document-policy engine.

Tenant admins configure, per document type, whether a document should be
auto-approved, sent to review, or rejected outright — plus a minimum confidence.
The pipeline applies this AFTER the field-level rules, and officers can see the
policy that applied to each document.
"""
from __future__ import annotations

import json
import os
import threading

from fastapi import HTTPException

from .models import DocumentType, RouteDecision

_DATA = os.path.join(os.path.dirname(__file__), "data", "business_rules.json")
_LOCK = threading.Lock()
_CACHE: dict | None = None

_ACTIONS = {"auto_approve", "review", "reject"}


def _load() -> dict:
    global _CACHE
    if _CACHE is None:
        with open(_DATA, encoding="utf-8") as fh:
            _CACHE = json.load(fh)
    return _CACHE


def config() -> dict:
    return _load()


def _policy_for(doc_type: str) -> dict | None:
    return next((p for p in _load().get("policies", []) if p["doc_type"] == doc_type), None)


def apply_policy(
    doc_type: DocumentType, decision: RouteDecision, min_conf: float, critical_failed: bool = False
) -> tuple[RouteDecision, list[str]]:
    """Override the base routing decision using the tenant's document policy."""
    cfg = _load()
    reasons: list[str] = []
    p = _policy_for(doc_type.value)

    if p is None:
        if cfg.get("auto_reject_unknown") and doc_type == DocumentType.UNKNOWN:
            return RouteDecision.REJECTED, ["policy: unknown document type is auto-rejected"]
        return decision, reasons

    action = p.get("action", "review")
    note = p.get("note", "")
    label = f"policy [{doc_type.value} → {action}]" + (f": {note}" if note else "")

    if action == "reject":
        return RouteDecision.REJECTED, [label]
    if action == "review":
        # Force review unless it already is; keep any existing reasons upstream.
        reasons.append(label)
        return (RouteDecision.NEEDS_REVIEW if decision != RouteDecision.REJECTED else decision), reasons
    if action == "auto_approve":
        threshold = cfg.get("min_confidence", 0.8)
        if decision == RouteDecision.NEEDS_REVIEW and min_conf >= threshold and not critical_failed:
            # Eligible for auto-approve, but only if no critical rule failed
            # (route() already keeps NEEDS_REVIEW when a critical rule fails).
            reasons.append(label + " (auto-approved by policy)")
            return RouteDecision.AUTO_APPROVED, reasons
        reasons.append(label)
        return decision, reasons
    return decision, reasons


# --------------------------------------------------------------------------- #
# Admin editing
# --------------------------------------------------------------------------- #
def update_config(new_cfg: dict) -> dict:
    global _CACHE
    policies = new_cfg.get("policies", [])
    cleaned = []
    seen = set()
    valid_types = {t.value for t in DocumentType}
    for p in policies:
        dt = p.get("doc_type")
        action = p.get("action")
        if dt not in valid_types or action not in _ACTIONS or dt in seen:
            continue
        seen.add(dt)
        cleaned.append({"doc_type": dt, "action": action, "note": (p.get("note") or "")[:200]})
    if not cleaned:
        raise HTTPException(status_code=400, detail="at least one valid policy is required")
    try:
        min_conf = float(new_cfg.get("min_confidence", 0.8))
    except (TypeError, ValueError):
        min_conf = 0.8
    cfg = {
        "min_confidence": max(0.0, min(1.0, min_conf)),
        "auto_reject_unknown": bool(new_cfg.get("auto_reject_unknown", False)),
        "policies": cleaned,
    }
    with _LOCK:
        with open(_DATA, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, indent=2)
        _CACHE = cfg
    return cfg
