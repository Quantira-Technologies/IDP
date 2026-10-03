"""Step 5 — Validate: run the business rules for the document type."""
from __future__ import annotations

from ..models import Extraction, RuleResult
from ..rules.engine import RuleContext, load_hs_rates
from ..rules.rulesets import rules_for


def validate(extraction: Extraction, siblings: list[Extraction]) -> list[RuleResult]:
    ctx = RuleContext(
        extraction=extraction,
        siblings=[s for s in siblings if s is not extraction],
        hs_rates=load_hs_rates(),
    )
    return [rule(ctx) for rule in rules_for(extraction.doc_type)]
