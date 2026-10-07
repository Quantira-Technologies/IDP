"""Field extraction from authoritative document text (PDF text-layer / DOCX).

Used when the upload already carries real text, so no OCR is needed. Handles the
common key/value shapes found in trade & finance documents:

  * "Key: value" / "Key | value"      (inline, incl. DOCX table rows)
  * "Key    value"                     (2+ spaces between label and value)
  * "Opening Balance 125,000.00"       (label followed by a numeric value)
  * "Statement No." <newline> "BS-01"  (label on its own line, value on the next)

Arabic labels are preserved verbatim as field names, so Arabic documents surface
Arabic keys and values.
"""
from __future__ import annotations

import re

from ..models import DocumentType, Extraction, Field, TextLine
from ..schema_registry import header_field_names
from .base import Extractor, RawDocument
from .ocr_extractor import _detect_table, _normalize_key

_NUM = re.compile(r"\d")
_INLINE_KV = re.compile(r"^\s*([^:|]{2,44}?)\s*[:|]\s*(.+?)\s*$")
_SPACED_KV = re.compile(r"^\s*([A-Za-z\u0600-\u06FF][\w .\u0600-\u06FF/#&-]{1,42}?)\s{2,}(\S.*)$")
_LABEL_NUM = re.compile(r"^\s*([A-Za-z\u0600-\u06FF][\w .\u0600-\u06FF/#&-]{1,42}?)\s+([\d][\d,./:\s-]*\d|\d)\s*$")

# Labels that commonly sit on their own line with the value on the next line.
_KNOWN_LABELS = {
    "statement no", "statement number", "account holder", "account no", "account number",
    "statement period", "period", "currency", "opening balance", "closing balance",
    "certificate no", "certificate number", "exporter", "consignee", "shipper",
    "importer", "destination country", "country of destination", "country of origin",
    "origin", "goods description", "description of goods", "description", "issue date",
    "date of issue", "invoice no", "invoice number", "invoice date", "date", "vendor",
    "supplier", "buyer", "seller", "po no", "po number", "purchase order", "total",
    "grand total", "subtotal", "tax", "vat", "gstin", "hawb no", "hawb", "flight",
    "gross weight", "net weight", "nationality", "passport no", "passport number",
}


def _is_known_label(line: str) -> bool:
    norm = re.sub(r"[^a-z0-9 ]", " ", line.lower()).strip()
    norm = re.sub(r"\s+", " ", norm)
    return norm in _KNOWN_LABELS


def _key(label: str) -> str:
    """Normalize an ASCII label; keep non-ASCII (Arabic) labels as-is."""
    k = _normalize_key(label)
    if not k:
        k = re.sub(r"\s+", " ", (label or "").strip())
    return k


def _clean_lines(text: str) -> list[str]:
    return [ln.strip() for ln in (text or "").splitlines() if ln.strip()]


def extract_fields_from_text(text: str, doc_type: DocumentType) -> dict[str, Field]:
    lines = _clean_lines(text)
    fields: dict[str, Field] = {}

    def add(label: str, value: str, conf: float = 0.97) -> None:
        key = _key(label)
        val = (value or "").strip()
        # Drop a redundant leading label echoed into the value ("Opening Balance 125" ->).
        if val.lower().startswith(label.strip().lower()):
            val = val[len(label.strip()):].strip(" :|-")
        if key and val and key not in fields and 0 < len(val) <= 180:
            fields[key] = Field(name=key, value=val, confidence=conf)

    i, n = 0, len(lines)
    while i < n:
        line = lines[i]

        m = _INLINE_KV.match(line)
        if m and m.group(2).strip():
            add(m.group(1), m.group(2))
            i += 1
            continue

        m = _LABEL_NUM.match(line)
        if m:
            add(m.group(1), m.group(2))
            i += 1
            continue

        m = _SPACED_KV.match(line)
        if m:
            add(m.group(1), m.group(2))
            i += 1
            continue

        # Stacked: a known label on its own line, value on the next.
        if i + 1 < n and _is_known_label(line):
            nxt = lines[i + 1]
            if not _is_known_label(nxt):
                add(line, nxt)
                i += 2
                continue
        i += 1

    # Schema order first, then any extra discovered fields.
    names = header_field_names(doc_type)
    ordered: dict[str, Field] = {}
    for k in names:
        if k in fields:
            ordered[k] = fields.pop(k)
    ordered.update(fields)
    return ordered


class TextExtractor(Extractor):
    name = "text"

    def extract(self, raw: RawDocument, doc_type: DocumentType) -> Extraction:
        text = raw.text
        lines = _clean_lines(text)

        fields = extract_fields_from_text(text, doc_type)

        # Detect a simple table from any 3+ column rows (e.g. DOCX line-item grids).
        synth = [
            {
                "text": ln,
                "conf": 0.97,
                "cells": [
                    {"text": c.strip(), "conf": 0.97, "bbox": None}
                    for c in re.split(r"\s{2,}|\t|\|", ln)
                    if c.strip()
                ],
            }
            for ln in lines
        ]
        table_columns, line_items = _detect_table(synth)

        full_text = [TextLine(text=ln, confidence=0.97, bbox=None) for ln in lines]

        # If nothing structured was found, still surface the real lines as fields.
        if len(fields) < 1:
            for idx, ln in enumerate(lines[:12], start=1):
                fields[f"line_{idx}"] = Field(name=f"line_{idx}", value=ln, confidence=0.9)

        source = "pdf" if (raw.content_type == "image/png" or (raw.name or "").lower().endswith(".pdf")) else "docx/text"
        return Extraction(
            doc_type=doc_type,
            engine=f"text:{source}",
            fields=fields,
            line_items=line_items,
            full_text=full_text,
            table_columns=table_columns,
        )
