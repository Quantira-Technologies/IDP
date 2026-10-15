"""Pipeline orchestrator — runs the six steps end to end.

  Classify -> Segment -> Select -> Extract -> Validate -> Route

Segmentation happens first at the bundle level so that each sub-document is then
classified, extracted, validated (with access to its bundle siblings for
cross-document rules), and routed independently.
"""
from __future__ import annotations

import uuid

from ..extractors.base import RawDocument
from ..models import (
    DocumentResult,
    Extraction,
    RuleSeverity,
    SubDocumentResult,
    workflow_of,
)
from .classify import classify
from .route import route
from .segment import segment
from .select import select_engine
from .validate import validate


def process_document(raw: RawDocument) -> DocumentResult:
    # Step 2 (bundle-level): split into sub-documents.
    sub_raws = segment(raw)

    # Steps 1, 3, 4: classify, select engine, extract — for each sub-document.
    extractions: list[Extraction] = []
    engines: list[str] = []
    doc_types = []
    for sub in sub_raws:
        doc_type = classify(sub)  # Step 1
        engine = select_engine(doc_type, sub)  # Step 3
        extraction = engine.extract(sub, doc_type)  # Step 4
        extractions.append(extraction)
        engines.append(engine.name)
        doc_types.append(doc_type)

    # Steps 5 & 6: validate (with sibling context) and route.
    sub_results: list[SubDocumentResult] = []
    for i, extraction in enumerate(extractions):
        rule_results = validate(extraction, extractions)  # Step 5
        decision, reasons, min_conf = route(extraction, rule_results)  # Step 6

        # Step 6b: apply the tenant's business-rule / document policy.
        from ..business_rules import apply_policy

        critical_failed = any(not r.passed and r.severity == RuleSeverity.CRITICAL for r in rule_results)
        decision, policy_reasons = apply_policy(extraction.doc_type, decision, min_conf, critical_failed)
        reasons = reasons + policy_reasons

        sub_results.append(
            SubDocumentResult(
                index=i,
                doc_type=extraction.doc_type,
                workflow=workflow_of(extraction.doc_type),
                engine=engines[i],
                extraction=extraction,
                rule_results=rule_results,
                min_confidence=min_conf,
                route=decision,
                route_reasons=reasons,
            )
        )

    return DocumentResult(
        id=str(uuid.uuid4()),
        source_name=raw.name,
        sub_documents=sub_results,
    )
