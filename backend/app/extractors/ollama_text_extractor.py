"""Text LLM extractor via an Ollama-compatible chat model (e.g. qwen2.5:1.5b).

Text models cannot read an image directly, so this path runs OCR first and then
asks the chat model to turn the recognised text into the schema's structured
fields:

    image -> Tesseract OCR (text + lines + QR) -> chat model -> {fields, line_items}

OCR still provides the verbatim `full_text`, QR codes and a best-effort source
bounding box for each field (by matching the value back to an OCR line), so the
"every field traced to source" promise is preserved even though the LLM itself
returns no coordinates.

If the model/gateway is unreachable, extraction falls back to the OCR result so
an upload never hard-fails; the engine label makes the fallback visible in the UI.
"""
from __future__ import annotations

from ..config import settings
from ..models import DocumentType, Extraction, Field, TextLine
from ..schema_registry import header_field_names, line_item_field_names
from . import ollama_client
from .base import Extractor, RawDocument
from .ollama_extractor import parse_extraction


def text_extraction_prompt(doc_type: DocumentType, ocr_text: str) -> list[dict]:
    """Build the chat messages: a system role + the OCR text and target schema."""
    headers = header_field_names(doc_type)
    line_fields = line_item_field_names(doc_type)

    schema_lines = [
        f"The document type is: {doc_type.value}.",
        "Extract these header fields (use the exact field names): "
        + (", ".join(headers) if headers else "(detect the key fields yourself)"),
    ]
    if line_fields:
        schema_lines.append(
            "If the document has a line-item table, extract one object per row with "
            f"these fields: {', '.join(line_fields)}."
        )

    system = (
        "You are an expert trade & finance document data extractor. "
        "You are given the raw OCR text of a single document. "
        "Return ONLY valid JSON, no prose, in exactly this shape:\n"
        '{ "fields": { "<field_name>": { "value": <string|number|null>, "confidence": <0..1> } }, '
        '"line_items": [ { "<field_name>": { "value": ..., "confidence": <0..1> } } ] }\n'
        "Rules:\n"
        "- Use null with confidence 0 for fields you cannot find.\n"
        "- confidence is your certainty from 0 to 1.\n"
        "- Do not invent values; only use what appears in the OCR text.\n"
        + "\n".join(schema_lines)
    )
    user = "OCR TEXT:\n\"\"\"\n" + (ocr_text or "").strip() + "\n\"\"\"\n\nReturn the JSON now."
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _assign_bboxes(fields: dict[str, Field], full_text: list[TextLine]) -> None:
    """Best-effort: point each field at the OCR line that contains its value."""
    for field in fields.values():
        if field.bbox is not None or field.value in (None, ""):
            continue
        needle = str(field.value).strip().lower()
        if len(needle) < 2:
            continue
        for line in full_text:
            if needle in line.text.lower():
                field.bbox = line.bbox
                break


class OllamaTextExtractor(Extractor):
    name = "ollama_text"

    def extract(self, raw: RawDocument, doc_type: DocumentType) -> Extraction:
        # Offline / canned documents have no image — keep them on the deterministic
        # mock path so demos and tests never depend on the network.
        if not raw.has_image:
            from .mock_extractor import MockExtractor

            return MockExtractor().extract(raw, doc_type)

        # A text model needs OCR text. Without Tesseract there's nothing to feed it,
        # so fall back to mock rather than hard-failing the upload.
        from .ocr_extractor import OCRExtractor, available as ocr_available

        if not ocr_available():
            from .mock_extractor import MockExtractor

            return MockExtractor().extract(raw, doc_type)

        # 1) OCR the page for text + lines + QR.
        base: Extraction = OCRExtractor().extract(raw, doc_type)
        ocr_text = "\n".join(line.text for line in base.full_text)

        if not ocr_text.strip():
            return base

        # 2) Ask the chat model to structure the OCR text; fall back to OCR on error.
        model = settings.ollama_model
        try:
            messages = text_extraction_prompt(doc_type, ocr_text)
            response = ollama_client.generate_chat(messages, want_json=True)
            result = parse_extraction(response, doc_type, engine=f"ollama-text:{model}")
        except Exception as exc:  # noqa: BLE001 — never hard-fail an upload
            base.engine = f"ocr (AI fallback: {type(exc).__name__})"
            return base

        # 3) Enrich LLM fields with OCR source (bbox) and carry over verbatim capture.
        _assign_bboxes(result.fields, base.full_text)
        result.full_text = base.full_text
        result.qr_codes = base.qr_codes
        result.table_columns = base.table_columns
        if not result.line_items:
            result.line_items = base.line_items
        if not result.fields:
            # Model returned nothing usable — keep OCR's fields so the UI isn't empty.
            result.fields = base.fields
            result.engine = f"ocr (AI returned no fields) · {model}"
        return result
