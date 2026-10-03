"""Tests for the Ollama vision extractor's pure parsing helpers and asset handling.

These do NOT require a running Ollama server — they exercise the JSON parsing,
bbox normalization, and doc-type classification logic offline.
"""
from __future__ import annotations

from app.assets import list_assets, raw_from_asset
from app.extractors.ollama_extractor import (
    parse_doc_type,
    parse_extraction,
)
from app.models import DocumentType


def test_parse_doc_type_variants():
    assert parse_doc_type("commercial_invoice") == DocumentType.COMMERCIAL_INVOICE
    assert parse_doc_type("  Vendor_Invoice \n") == DocumentType.VENDOR_INVOICE
    assert parse_doc_type("This is a bank_statement") == DocumentType.BANK_STATEMENT
    assert parse_doc_type("nonsense") == DocumentType.UNKNOWN


def test_parse_extraction_objects_with_confidence_and_bbox():
    text = """```json
    {
      "fields": {
        "invoice_number": {"value": "INV-1", "confidence": 0.95, "bbox": [0.1, 0.1, 0.2, 0.03]},
        "grand_total": {"value": 100.0, "confidence": 0.9}
      },
      "line_items": [
        {"hs_code": {"value": "7318.15.00", "confidence": 0.8},
         "amount": {"value": 100.0, "confidence": 0.9}}
      ]
    }
    ```"""
    ex = parse_extraction(text, DocumentType.COMMERCIAL_INVOICE)
    assert ex.fields["invoice_number"].value == "INV-1"
    assert ex.fields["invoice_number"].bbox is not None
    assert ex.fields["grand_total"].bbox is None
    assert len(ex.line_items) == 1
    assert ex.line_items[0].fields["hs_code"].value == "7318.15.00"


def test_parse_extraction_bare_values_and_pixel_bbox():
    # Model returned bare values and a 0..1000 style bbox — should still parse.
    text = '{"fields": {"currency": "USD", "grand_total": {"value": 5, "bbox": [100, 200, 300, 40]}}}'
    ex = parse_extraction(text, DocumentType.COMMERCIAL_INVOICE)
    assert ex.fields["currency"].value == "USD"
    box = ex.fields["grand_total"].bbox
    assert box is not None and 0.0 <= box.x <= 1.0 and box.width > 0


def test_parse_extraction_bad_json_is_safe():
    ex = parse_extraction("not json at all", DocumentType.GST_CERTIFICATE)
    assert ex.doc_type == DocumentType.GST_CERTIFICATE
    assert ex.fields == {}


def test_sample_assets_present_and_loadable():
    names = list_assets()
    assert len(names) > 0
    raw = raw_from_asset(names[0])
    assert raw.has_image is True
    assert raw.content_type and raw.content_type.startswith("image/")


def test_asset_path_traversal_blocked():
    import pytest

    with pytest.raises(FileNotFoundError):
        raw_from_asset("../config.py")
