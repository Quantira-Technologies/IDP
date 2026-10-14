"""Tests for native-text (PDF text-layer / DOCX) field extraction."""
from __future__ import annotations

from app.extractors.base import RawDocument, RawPage
from app.extractors.text_extractor import TextExtractor, extract_fields_from_text
from app.models import DocumentType

_BANK_EN = """Bank Statement
Statement No.
BS-2026-001
Account Holder
Gulf Foods Import Co.
Currency
USD
Opening Balance 125,000.00
Closing Balance 142,450.00
"""

_COO_AR = """شهادة منشأ
رقم الشهادة  |  شهادة-منشأ-001
المُصدّر  |  شركة كامارو للتجارة ذ.م.م
بلد المنشأ  |  الهند
تاريخ الإصدار  |  2026-10-06
"""


def test_english_bank_statement_fields():
    f = extract_fields_from_text(_BANK_EN, DocumentType.BANK_STATEMENT)
    assert f["opening_balance"].value == "125,000.00"
    assert f["closing_balance"].value == "142,450.00"
    assert f["currency"].value == "USD"
    assert f["statement_no"].value == "BS-2026-001"
    assert f["account_holder"].value == "Gulf Foods Import Co."
    # No mock/placeholder values leaked in.
    assert all("ACME-INV" not in str(fld.value) for fld in f.values())


def test_arabic_keys_and_values_preserved():
    f = extract_fields_from_text(_COO_AR, DocumentType.CERTIFICATE_OF_ORIGIN)
    assert f["رقم الشهادة"].value == "شهادة-منشأ-001"
    assert f["بلد المنشأ"].value == "الهند"
    assert f["تاريخ الإصدار"].value == "2026-10-06"


def test_text_extractor_populates_full_text_and_engine():
    raw = RawDocument(name="stmt.docx", pages=[RawPage(0, _BANK_EN)], text_is_native=True)
    ex = TextExtractor().extract(raw, DocumentType.BANK_STATEMENT)
    assert ex.engine.startswith("text:")
    assert len(ex.full_text) >= 5
    assert ex.fields  # real fields, not empty


def test_default_extractor_never_serves_mock_for_real_uploads(monkeypatch):
    # Deployments ship no .env, so the code default must extract real content.
    from app.config import Settings
    from app.extractors import base

    monkeypatch.setattr(base, "settings", Settings(_env_file=None))
    raw = RawDocument(name="stmt.docx", pages=[RawPage(0, _BANK_EN)], text_is_native=True)
    assert base.get_extractor(raw).name == "text"
