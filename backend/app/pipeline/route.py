"""Step 6 — Route: auto-approve confident, rule-clean docs; else human review.

A document is auto-approved only when BOTH hold:
  * every field's confidence >= the configured threshold, AND
  * no CRITICAL rule failed.
Anything else is routed to the review queue with the reasons attached.
"""
from __future__ import annotations

from ..config import settings
from ..models import (
    Extraction,
    RouteDecision,
    RuleResult,
    RuleSeverity,
)


def route(
    extraction: Extraction, rule_results: list[RuleResult]
) -> tuple[RouteDecision, list[str], float]:
    reasons: list[str] = []

    min_conf = extraction.min_confidence()
    if min_conf < settings.confidence_threshold:
        low = _low_confidence_fields(extraction)
        reasons.append(
            f"low confidence (min={min_conf:.2f} < {settings.confidence_threshold:.2f}): {', '.join(low)}"
        )

    for r in rule_results:
        if not r.passed and r.severity == RuleSeverity.CRITICAL:
            reasons.append(f"failed critical rule '{r.rule_id}': {r.detail}")

    decision = RouteDecision.AUTO_APPROVED if not reasons else RouteDecision.NEEDS_REVIEW
    return decision, reasons, min_conf


def _low_confidence_fields(extraction: Extraction) -> list[str]:
    out: list[str] = []
    for name, f in extraction.fields.items():
        if f.confidence < settings.confidence_threshold:
            out.append(name)
    for i, li in enumerate(extraction.line_items):
        for name, f in li.fields.items():
            if f.confidence < settings.confidence_threshold:
                out.append(f"line{i+1}.{name}")
    return out
