"""Tests for the end-to-end pipeline: bundle splitting, routing, corrections."""
from __future__ import annotations

from app.config import settings
from app.models import DocumentType, RouteDecision
from app.pipeline.orchestrator import process_document
from app.pipeline.route import route
from app.pipeline.validate import validate
from app.samples import demo_bundle


def test_bundle_splits_into_two_subdocuments():
    result = process_document(demo_bundle())
    assert len(result.sub_documents) == 2
    types = {s.doc_type for s in result.sub_documents}
    assert types == {DocumentType.COMMERCIAL_INVOICE, DocumentType.CERTIFICATE_OF_ORIGIN}


def test_every_field_has_bbox_traceability():
    result = process_document(demo_bundle())
    for sub in result.sub_documents:
        for f in sub.extraction.fields.values():
            assert f.bbox is not None
        for li in sub.extraction.line_items:
            for f in li.fields.values():
                assert f.bbox is not None


def test_invoice_routes_to_review_due_to_duty_mismatch():
    result = process_document(demo_bundle())
    invoice = next(
        s for s in result.sub_documents if s.doc_type == DocumentType.COMMERCIAL_INVOICE
    )
    assert invoice.route == RouteDecision.NEEDS_REVIEW
    assert any("hs_code_duty_consistency" in r for r in invoice.route_reasons)


def test_correcting_duty_rate_flips_route_to_approved():
    result = process_document(demo_bundle())
    invoice = next(
        s for s in result.sub_documents if s.doc_type == DocumentType.COMMERCIAL_INVOICE
    )
    # Fix the seeded bad duty rate on line 2 (7318.15.00 -> 7.5%).
    invoice.extraction.line_items[1].fields["applied_duty_rate"].value = 7.5
    invoice.extraction.line_items[1].fields["applied_duty_rate"].confidence = 1.0

    siblings = [s.extraction for s in result.sub_documents]
    rule_results = validate(invoice.extraction, siblings)
    decision, reasons, _ = route(invoice.extraction, rule_results)
    assert decision == RouteDecision.AUTO_APPROVED, reasons
