"""Tests for the Po2Pay, Contract, and Finance workflows added on top of Customs."""
from __future__ import annotations

from app.models import DocumentType, RouteDecision, Workflow, workflow_of
from app.pipeline.orchestrator import process_document
from app.rules.engine import gstin_check_digit, is_valid_gstin
from app.samples import DEMO_BUNDLES, po2pay_bundle


def test_workflow_mapping():
    assert workflow_of(DocumentType.COMMERCIAL_INVOICE) == Workflow.CUSTOMS
    assert workflow_of(DocumentType.VENDOR_INVOICE) == Workflow.PO2PAY
    assert workflow_of(DocumentType.GST_CERTIFICATE) == Workflow.CONTRACTS
    assert workflow_of(DocumentType.BANK_STATEMENT) == Workflow.FINANCE


def test_po2pay_bundle_three_documents():
    result = process_document(po2pay_bundle())
    types = {s.doc_type for s in result.sub_documents}
    assert types == {
        DocumentType.PURCHASE_ORDER,
        DocumentType.GOODS_RECEIPT_NOTE,
        DocumentType.VENDOR_INVOICE,
    }


def test_three_way_match_catches_overbilling():
    result = process_document(po2pay_bundle())
    inv = next(s for s in result.sub_documents if s.doc_type == DocumentType.VENDOR_INVOICE)
    rules = {r.rule_id: r for r in inv.rule_results}
    # Line ANC-M10 bills 100 but only 90 were received and price differs from PO.
    assert rules["three_way_match"].passed is False
    assert inv.route == RouteDecision.NEEDS_REVIEW


def test_gstin_checksum():
    assert gstin_check_digit("27AAPFU0939F1Z") == "V"
    assert is_valid_gstin("27AAPFU0939F1ZV") is True
    assert is_valid_gstin("27AAPFU0939F1ZX") is False


def test_gst_certificate_validates_then_policy_reviews():
    result = process_document(DEMO_BUNDLES["contracts"]())
    gst = next(s for s in result.sub_documents if s.doc_type == DocumentType.GST_CERTIFICATE)
    rules = {r.rule_id: r for r in gst.rule_results}
    assert rules["gstin_checksum"].passed is True
    # Tenant policy routes GST certificates to review.
    assert gst.route == RouteDecision.NEEDS_REVIEW


def test_bank_statement_reconciles_then_policy_rejects():
    result = process_document(DEMO_BUNDLES["finance"]())
    stmt = next(s for s in result.sub_documents if s.doc_type == DocumentType.BANK_STATEMENT)
    rules = {r.rule_id: r for r in stmt.rule_results}
    assert rules["running_balance"].passed is True
    # Bank statements are out of customs scope -> policy rejects them.
    assert stmt.route == RouteDecision.REJECTED
