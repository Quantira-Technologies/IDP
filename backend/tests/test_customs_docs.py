"""Tests for the two new customs document types learned from the real samples:
House Air Waybill and Traveler Customs Declaration.
"""
from __future__ import annotations

from app.extractors.base import RawDocument, RawPage
from app.models import DocumentType, RouteDecision, Workflow, workflow_of
from app.pipeline.classify import classify
from app.pipeline.orchestrator import process_document
from app.samples import raw_from_upload
from app.schema_registry import header_field_names


def test_new_types_mapped_to_customs():
    assert workflow_of(DocumentType.HOUSE_AIR_WAYBILL) == Workflow.CUSTOMS
    assert workflow_of(DocumentType.CUSTOMS_DECLARATION) == Workflow.CUSTOMS


def test_new_type_schemas_have_fields():
    assert "hawb_number" in header_field_names(DocumentType.HOUSE_AIR_WAYBILL)
    assert "passport_number" in header_field_names(DocumentType.CUSTOMS_DECLARATION)


def test_classify_house_air_waybill_and_declaration():
    hawb = RawDocument(name="x", pages=[RawPage(0, "HOUSE AIR WAYBILL HAWB No 123")])
    assert classify(hawb) == DocumentType.HOUSE_AIR_WAYBILL
    decl = RawDocument(name="y", pages=[RawPage(0, "SAUDI CUSTOMS DECLARATION Traveler Information")])
    assert classify(decl) == DocumentType.CUSTOMS_DECLARATION


def test_house_air_waybill_extracts_and_routes():
    raw = raw_from_upload("house_air_waybill.jpeg", b"", "image/jpeg")
    result = process_document(raw)
    sub = result.sub_documents[0]
    assert sub.doc_type == DocumentType.HOUSE_AIR_WAYBILL
    rules = {r.rule_id: r for r in sub.rule_results}
    assert rules["required_hawb_fields"].passed is True
    assert rules["hawb_weight_consistency"].passed is True
    assert sub.route == RouteDecision.AUTO_APPROVED


def test_customs_declaration_extracts_required_identity():
    raw = raw_from_upload("customs_declaration.jpeg", b"", "image/jpeg")
    result = process_document(raw)
    sub = result.sub_documents[0]
    assert sub.doc_type == DocumentType.CUSTOMS_DECLARATION
    rules = {r.rule_id: r for r in sub.rule_results}
    assert rules["required_declaration_fields"].passed is True
