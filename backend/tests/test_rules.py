"""Tests for the word-to-number helper and business rules."""
from __future__ import annotations

from app.models import DocumentType
from app.pipeline.orchestrator import process_document
from app.rules.engine import words_to_number
from app.samples import demo_bundle


def test_words_to_number_with_cents():
    val = words_to_number("FOUR THOUSAND THREE HUNDRED EIGHTY ONE AND CENTS TWELVE")
    assert val == 4381.12


def test_words_to_number_unparseable():
    assert words_to_number("") is None
    assert words_to_number("gibberish tokens here") is None


def test_invoice_rules_catch_duty_mismatch():
    result = process_document(demo_bundle())
    invoice = next(
        s for s in result.sub_documents if s.doc_type == DocumentType.COMMERCIAL_INVOICE
    )
    rules = {r.rule_id: r for r in invoice.rule_results}

    # Line totals must sum correctly and amount-in-words must match.
    assert rules["line_totals_sum"].passed is True
    assert rules["amount_in_words_matches"].passed is True
    # The seeded duty-rate inconsistency on line 2 must be caught.
    assert rules["hs_code_duty_consistency"].passed is False


def test_coo_cross_check_passes_in_bundle():
    result = process_document(demo_bundle())
    coo = next(
        s for s in result.sub_documents if s.doc_type == DocumentType.CERTIFICATE_OF_ORIGIN
    )
    rules = {r.rule_id: r for r in coo.rule_results}
    assert rules["coo_invoice_cross_check"].passed is True
