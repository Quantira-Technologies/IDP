"""Ollama vision extractor (real AI path).

Uses a local multimodal model (default `qwen2.5vl:3b`) to:
  1. classify the document image into one of the known document types, and
  2. extract the schema's fields as structured JSON with self-reported confidence
     and optional bounding boxes.

The extraction prompt is built from `app/schemas/*.json`, so adding a document
type needs only a schema + ruleset — no changes here.

Parsing is split into pure helpers (`parse_extraction`, `parse_doc_type`) so the
JSON-handling logic is unit-testable without a running Ollama server.
"""
from __future__ import annotations

import json
import re

from ..models import BoundingBox, DocumentType, Extraction, Field, LineItem
from ..schema_registry import get_schema, header_field_names, line_item_field_names
from . import ollama_client
from .base import Extractor, RawDocument

_DEFAULT_CONFIDENCE = 0.85

_CLASSIFY_LABELS = [
    "commercial_invoice",
    "certificate_of_origin",
    "house_air_waybill",
    "customs_declaration",
    "purchase_order",
    "goods_receipt_note",
    "vendor_invoice",
    "gst_certificate",
    "bank_statement",
    "unknown",
]


# --------------------------------------------------------------------------- #
# Pure helpers (unit-testable, no network)
# --------------------------------------------------------------------------- #
def classify_prompt() -> str:
    labels = ", ".join(_CLASSIFY_LABELS)
    return (
        "You are a trade/finance document classifier. Look at this document image "
        "and decide which single type it is. Respond with ONLY one of these exact "
        f"labels and nothing else: {labels}."
    )


def parse_doc_type(text: str) -> DocumentType:
    token = (text or "").strip().lower()
    token = re.sub(r"[^a-z_]", "", token.replace(" ", "_"))
    for label in _CLASSIFY_LABELS:
        if label in token:
            try:
                return DocumentType(label)
            except ValueError:
                break
    return DocumentType.UNKNOWN


def extraction_prompt(doc_type: DocumentType) -> str:
    schema = get_schema(doc_type) or {}
    title = schema.get("title", doc_type.value)
    headers = header_field_names(doc_type)
    line_fields = line_item_field_names(doc_type)

    lines = [
        f"You are an expert document data extractor. This is a {title}.",
        "Read the image and extract the fields below. Return ONLY valid JSON.",
        "",
        "JSON shape:",
        "{",
        '  "fields": { "<field_name>": { "value": <string|number|null>, '
        '"confidence": <0..1>, "bbox": [x, y, width, height] } },',
        '  "line_items": [ { "<field_name>": { "value": ..., "confidence": ..., "bbox": [...] } } ]',
        "}",
        "",
        "Rules:",
        "- bbox is OPTIONAL, coordinates normalized 0..1 relative to the page; omit if unsure.",
        "- confidence is your certainty 0..1.",
        "- If a field is not present, use null with confidence 0.",
        "",
        f"Header fields to extract: {', '.join(headers) if headers else '(none)'}",
    ]
    if line_fields:
        lines.append(
            f"Each line item has these fields: {', '.join(line_fields)}. "
            "Return one object per line/row you see."
        )
    return "\n".join(lines)


def _coerce_json(text: str) -> dict:
    """Best-effort extraction of a JSON object from a model response."""
    if not text:
        return {}
    text = text.strip()
    # Strip markdown fences if present.
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fall back to the first {...} block.
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return {}
    return {}


def _normalize_bbox(raw_bbox, page: int = 0) -> BoundingBox | None:
    if not isinstance(raw_bbox, (list, tuple)) or len(raw_bbox) != 4:
        return None
    try:
        vals = [float(v) for v in raw_bbox]
    except (TypeError, ValueError):
        return None
    # Some models return 0..1000 (or pixels) instead of 0..1 — scale down.
    if max(vals) > 1.0:
        scale = 1000.0 if max(vals) <= 1000.0 else max(vals)
        vals = [v / scale for v in vals]
    x, y, w, h = vals
    if w <= 0 or h <= 0:
        return None
    clamp = lambda v: max(0.0, min(1.0, v))  # noqa: E731
    return BoundingBox(page=page, x=clamp(x), y=clamp(y), width=clamp(w), height=clamp(h))


def _to_field(name: str, raw) -> Field:
    """Accept either a bare value or an object {value, confidence, bbox}."""
    if isinstance(raw, dict):
        value = raw.get("value")
        conf = raw.get("confidence", _DEFAULT_CONFIDENCE)
        bbox = _normalize_bbox(raw.get("bbox"))
    else:
        value, conf, bbox = raw, _DEFAULT_CONFIDENCE, None
    try:
        conf = float(conf)
    except (TypeError, ValueError):
        conf = _DEFAULT_CONFIDENCE
    conf = max(0.0, min(1.0, conf))
    return Field(name=name, value=value, confidence=conf, bbox=bbox)


def parse_extraction(text: str, doc_type: DocumentType, engine: str = "ollama") -> Extraction:
    data = _coerce_json(text)
    raw_fields = data.get("fields") if isinstance(data.get("fields"), dict) else {}
    raw_lines = data.get("line_items") if isinstance(data.get("line_items"), list) else []

    # Prefer schema order; append any extra fields the model returned.
    names = header_field_names(doc_type)
    ordered = list(dict.fromkeys(names + [n for n in raw_fields.keys() if n not in names]))

    fields: dict[str, Field] = {}
    for name in ordered:
        if name in raw_fields:
            fields[name] = _to_field(name, raw_fields[name])

    line_items: list[LineItem] = []
    for row in raw_lines:
        if not isinstance(row, dict):
            continue
        li_fields = {name: _to_field(name, val) for name, val in row.items()}
        if li_fields:
            line_items.append(LineItem(fields=li_fields))

    return Extraction(doc_type=doc_type, engine=engine, fields=fields, line_items=line_items)


# --------------------------------------------------------------------------- #
# Extractor
# --------------------------------------------------------------------------- #
class OllamaExtractor(Extractor):
    name = "ollama"

    def extract(self, raw: RawDocument, doc_type: DocumentType) -> Extraction:
        if not raw.has_image:
            raise RuntimeError(
                "EXTRACTOR=ollama needs an image. Upload a JPEG/PNG (or use an asset). "
                "For text-only offline demos use EXTRACTOR=mock."
            )
        response = ollama_client.generate_vision(
            extraction_prompt(doc_type), raw.image_bytes, want_json=True
        )
        return parse_extraction(response, doc_type, engine=f"ollama:{self.name}")
