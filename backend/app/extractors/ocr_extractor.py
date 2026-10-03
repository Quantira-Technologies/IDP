"""Real OCR extractor (offline) — reads the WHOLE document, not just a few fields.

Pipeline:
  1. Clean the image (deskew, denoise, upscale, threshold) so blurry/pixelated
     scans become legible  ->  image_ops.preprocess_for_ocr
  2. OCR with Tesseract (eng+ara) to get every word + box + confidence.
  3. Capture: (a) every line verbatim (full_text), (b) labelled header fields
     (key/value), (c) a detected table / bill-of-materials as line items,
     (d) any QR codes (decoded + snapshotted separately).

Low-confidence tokens are dropped so we never surface OCR garbage. If Tesseract
is missing, `available()` is False and callers fall back to the mock extractor.
"""
from __future__ import annotations

import os
import re
import shutil
from functools import lru_cache

from ..models import BoundingBox, DocumentType, Extraction, Field, LineItem, TextLine
from ..schema_registry import header_field_names
from . import image_ops, qr
from .base import Extractor, RawDocument

_MIN_TOKEN_CONF = 0.35  # drop words below this so we never show random noise

_ALIASES: dict[str, str] = {
    "invoice no": "invoice_number", "invoice number": "invoice_number", "invoice #": "invoice_number",
    "inv no": "invoice_number", "tax invoice": "invoice_number", "bill no": "invoice_number",
    "invoice date": "invoice_date", "date": "invoice_date", "dated": "invoice_date",
    "po no": "po_number", "po number": "po_number", "purchase order": "po_number",
    "grand total": "grand_total", "total amount": "grand_total", "total": "grand_total",
    "net amount": "grand_total", "amount due": "grand_total", "total to pay": "grand_total",
    "currency": "currency", "gstin": "gstin", "gst no": "gstin", "gstin no": "gstin",
    "hawb no": "hawb_number", "hawb": "hawb_number", "awb no": "hawb_number",
    "certificate no": "certificate_number", "certificate number": "certificate_number",
    "country of origin": "country_of_origin", "origin": "country_of_origin",
    "exporter": "exporter", "consignee": "consignee", "shipper": "shipper",
    "vendor": "vendor", "supplier": "vendor", "seller": "exporter",
    "account no": "account_number", "account number": "account_number", "a/c no": "account_number",
    "opening balance": "opening_balance", "closing balance": "closing_balance",
    "passport no": "passport_number", "passport number": "passport_number",
    "nationality": "nationality", "flight": "flight_number", "flight no": "flight_number",
}


@lru_cache(maxsize=1)
def _configure() -> bool:
    try:
        import pytesseract
    except Exception:
        return False
    if shutil.which("tesseract"):
        return True
    for path in (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Tesseract-OCR", "tesseract.exe"),
        "/usr/bin/tesseract",
        "/opt/homebrew/bin/tesseract",
    ):
        if path and os.path.isfile(path):
            pytesseract.pytesseract.tesseract_cmd = path
            return True
    return False


@lru_cache(maxsize=1)
def available() -> bool:
    try:
        _configure()
        import pytesseract

        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


@lru_cache(maxsize=1)
def _langs() -> set[str]:
    try:
        import pytesseract

        return set(pytesseract.get_languages(config=""))
    except Exception:
        return {"eng"}


def _normalize_key(label: str) -> str:
    key = re.sub(r"[^a-z0-9 ]", " ", label.lower()).strip()
    key = re.sub(r"\s+", " ", key)
    return _ALIASES.get(key, key.replace(" ", "_"))


# --------------------------------------------------------------------------- #
# OCR + line/word reconstruction
# --------------------------------------------------------------------------- #
def _ocr_lines(image_bytes: bytes):
    """Return (lines, width, height). Each line: text, conf, y0, bbox, cells."""
    import pytesseract

    _configure()
    pil = image_ops.preprocess_for_ocr(image_bytes)
    w, h = pil.size
    lang = "eng+ara" if "ara" in _langs() else "eng"
    data = pytesseract.image_to_data(
        pil, lang=lang, config="--oem 3 --psm 3", output_type=pytesseract.Output.DICT
    )

    grouped: dict[tuple, list[int]] = {}
    n = len(data["text"])
    for i in range(n):
        txt = (data["text"][i] or "").strip()
        try:
            conf = float(data["conf"][i])
        except (TypeError, ValueError):
            conf = -1.0
        if not txt or conf < _MIN_TOKEN_CONF * 100:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        grouped.setdefault(key, []).append(i)

    gap_thresh = 0.028 * w
    lines = []
    for idxs in grouped.values():
        idxs.sort(key=lambda i: data["left"][i])
        words = [
            {
                "t": data["text"][i].strip(),
                "x0": data["left"][i], "x1": data["left"][i] + data["width"][i],
                "y0": data["top"][i], "y1": data["top"][i] + data["height"][i],
                "c": float(data["conf"][i]) / 100.0,
            }
            for i in idxs
        ]
        if not words:
            continue
        text = " ".join(wd["t"] for wd in words)
        x0 = min(wd["x0"] for wd in words); x1 = max(wd["x1"] for wd in words)
        y0 = min(wd["y0"] for wd in words); y1 = max(wd["y1"] for wd in words)
        conf = sum(wd["c"] for wd in words) / len(words)

        cells = []
        cur = [words[0]]
        for prev, wd in zip(words, words[1:]):
            if wd["x0"] - prev["x1"] > gap_thresh:
                cells.append(cur)
                cur = [wd]
            else:
                cur.append(wd)
        cells.append(cur)

        lines.append({
            "text": text,
            "conf": conf,
            "y0": y0,
            "bbox": BoundingBox(page=0, x=x0 / w, y=y0 / h, width=(x1 - x0) / w, height=(y1 - y0) / h),
            "cells": [
                {
                    "text": " ".join(cw["t"] for cw in cell),
                    "conf": sum(c["c"] for c in cell) / len(cell),
                    "bbox": BoundingBox(
                        page=0,
                        x=min(c["x0"] for c in cell) / w,
                        y=min(c["y0"] for c in cell) / h,
                        width=(max(c["x1"] for c in cell) - min(c["x0"] for c in cell)) / w,
                        height=(max(c["y1"] for c in cell) - min(c["y0"] for c in cell)) / h,
                    ),
                }
                for cell in cells
            ],
        })

    lines.sort(key=lambda l: l["y0"])
    return lines, w, h


def ocr_text(image_bytes: bytes) -> str:
    """Full document text (used by the classifier)."""
    try:
        lines, _w, _h = _ocr_lines(image_bytes)
        return "\n".join(l["text"] for l in lines)
    except Exception:
        return ""


_KV = re.compile(r"^\s*([A-Za-z][A-Za-z0-9 /#\.\-]{1,40}?)\s*[:\-]\s*(.+?)\s*$")
_KV2 = re.compile(r"^\s*([A-Za-z][A-Za-z0-9 /#\.]{2,32}?)\s{2,}(.+?)\s*$")
_NUMISH = re.compile(r"\d")


def _header_fields(lines, doc_type: DocumentType) -> dict[str, Field]:
    fields: dict[str, Field] = {}

    def add(name: str, value: str, conf: float, bbox) -> None:
        v = (value or "").strip()
        if not name or name in fields or not v or len(v) > 140:
            return
        fields[name] = Field(name=name, value=v, confidence=round(min(0.99, max(0.4, conf)), 3), bbox=bbox)

    for ln in lines:
        if len(ln["cells"]) <= 2:
            m = _KV.match(ln["text"]) or _KV2.match(ln["text"])
            if m:
                add(_normalize_key(m.group(1)), m.group(2), ln["conf"], ln["bbox"])

    ordered: dict[str, Field] = {}
    for k in header_field_names(doc_type):
        if k in fields:
            ordered[k] = fields.pop(k)
    ordered.update(fields)
    return ordered


def _detect_table(lines) -> tuple[list[str], list[LineItem]]:
    """Find rows that each have >=3 aligned cells (a bill-of-materials / grid)."""
    rows = [ln for ln in lines if len(ln["cells"]) >= 3]
    if len(rows) < 2:
        return [], []

    ncols = max(len(r["cells"]) for r in rows)
    header_row = rows[0]
    header_is_text = sum(1 for c in header_row["cells"] if not _NUMISH.search(c["text"])) >= max(2, len(header_row["cells"]) - 1)
    if header_is_text and len(header_row["cells"]) >= ncols - 1:
        columns = [_normalize_key(c["text"]) or f"col_{i+1}" for i, c in enumerate(header_row["cells"])]
        body = rows[1:]
    else:
        columns = [f"col_{i+1}" for i in range(ncols)]
        body = rows

    items: list[LineItem] = []
    for r in body:
        li_fields: dict[str, Field] = {}
        for i, cell in enumerate(r["cells"][:ncols]):
            name = columns[i] if i < len(columns) else f"col_{i+1}"
            if name in li_fields:
                name = f"{name}_{i+1}"
            li_fields[name] = Field(
                name=name, value=cell["text"],
                confidence=round(min(0.99, max(0.4, cell["conf"])), 3), bbox=cell["bbox"],
            )
        if li_fields:
            items.append(LineItem(fields=li_fields))

    if len(items) < 2:
        return [], []
    return columns, items


class OCRExtractor(Extractor):
    name = "ocr"

    def extract(self, raw: RawDocument, doc_type: DocumentType) -> Extraction:
        if not raw.has_image:
            return Extraction(doc_type=doc_type, engine="ocr", fields={}, line_items=[])

        lines, _w, _h = _ocr_lines(raw.image_bytes)

        fields = _header_fields(lines, doc_type)
        table_columns, line_items = _detect_table(lines)
        full_text = [
            TextLine(text=ln["text"], confidence=round(ln["conf"], 3), bbox=ln["bbox"]) for ln in lines
        ]
        qr_codes = qr.detect_qr_codes(raw.image_bytes)

        if len(fields) < 3:
            ranked = sorted(full_text, key=lambda t: (t.confidence, len(t.text)), reverse=True)
            for i, tl in enumerate(ranked[:10], start=1):
                fields[f"line_{i}"] = Field(name=f"line_{i}", value=tl.text, confidence=tl.confidence, bbox=tl.bbox)

        langs = "+".join(sorted(_langs() & {"eng", "ara"})) or "eng"
        return Extraction(
            doc_type=doc_type,
            engine=f"ocr:tesseract ({langs})",
            fields=fields,
            line_items=line_items,
            full_text=full_text,
            qr_codes=qr_codes,
            table_columns=table_columns,
        )
