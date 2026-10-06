"""Unit tests for the text-model (Ollama chat) extraction path.

These do not touch the network: the chat transport is monkeypatched and the
no-image path is deterministic (it uses the offline mock extractor).
"""
from __future__ import annotations

from app.extractors import ollama_client
from app.extractors.base import RawDocument, RawPage
from app.extractors.ollama_text_extractor import (
    OllamaTextExtractor,
    _assign_bboxes,
    text_extraction_prompt,
)
from app.models import BoundingBox, DocumentType, Field, TextLine
from app.schema_registry import header_field_names


def test_prompt_includes_schema_fields_and_ocr_text():
    msgs = text_extraction_prompt(DocumentType.COMMERCIAL_INVOICE, "Invoice No: INV-9")
    assert [m["role"] for m in msgs] == ["system", "user"]
    assert "JSON" in msgs[0]["content"]
    names = header_field_names(DocumentType.COMMERCIAL_INVOICE)
    if names:
        assert any(n in msgs[0]["content"] for n in names)
    assert "Invoice No: INV-9" in msgs[1]["content"]


def test_generate_chat_parses_native_ollama_shape(monkeypatch):
    monkeypatch.setattr(
        ollama_client, "_post",
        lambda path, payload, timeout: {"message": {"role": "assistant", "content": '{"fields": {}}'}},
    )
    out = ollama_client.generate_chat([{"role": "user", "content": "hi"}], want_json=True)
    assert out == '{"fields": {}}'


def test_generate_chat_parses_openai_compatible_shape(monkeypatch):
    monkeypatch.setattr(
        ollama_client, "_post",
        lambda path, payload, timeout: {"choices": [{"message": {"content": "hello"}}]},
    )
    assert ollama_client.generate_chat([{"role": "user", "content": "hi"}]) == "hello"


def test_generate_chat_sends_bearer_token_when_configured(monkeypatch):
    monkeypatch.setattr(ollama_client.settings, "ollama_api_key", "secret-key")
    headers = ollama_client._headers()
    assert headers["Authorization"] == "Bearer secret-key"


def test_assign_bboxes_points_field_at_its_source_line():
    bbox = BoundingBox(x=0.1, y=0.2, width=0.3, height=0.1)
    fields = {"invoice_number": Field(name="invoice_number", value="INV-9", confidence=0.9)}
    lines = [TextLine(text="Invoice No: INV-9", confidence=0.9, bbox=bbox)]
    _assign_bboxes(fields, lines)
    assert fields["invoice_number"].bbox is bbox


def test_no_image_document_uses_offline_mock(monkeypatch):
    # Even with the text engine selected, a canned (image-less) document must stay
    # deterministic and never call the network.
    def _boom(*args, **kwargs):
        raise AssertionError("network must not be called for image-less documents")

    monkeypatch.setattr(ollama_client, "generate_chat", _boom)
    raw = RawDocument(
        name="commercial_invoice",
        pages=[RawPage(0, "ACME COMMERCIAL INVOICE  Invoice No INV-1  Total 100")],
    )
    result = OllamaTextExtractor().extract(raw, DocumentType.COMMERCIAL_INVOICE)
    assert "mock" in result.engine.lower()
