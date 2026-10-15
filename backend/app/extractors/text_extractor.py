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

from ..models import BoundingBox, DocumentType, Extraction, Field, LineItem, TextLine
from ..schema_registry import header_field_names
from .base import Extractor, RawDocument
from .ocr_extractor import _detect_table, _normalize_key

_NUM = re.compile(r"\d")
_INLINE_KV = re.compile(r"^\s*([^:|]{2,44}?)\s*[:|]\s*(.+?)\s*$")
_SPACED_KV = re.compile(r"^\s*([A-Za-z\u0600-\u06FF][\w .\u0600-\u06FF/#&-]{1,42}?)\s{2,}(\S.*)$")
_LABEL_NUM = re.compile(r"^\s*([A-Za-z\u0600-\u06FF][\w .\u0600-\u06FF/#&-]{1,42}?)\s+([\d][\d,./:\s-]*\d|\d)\s*$")
_TRAILING_COLON = re.compile(r"^\s*([^:|]{2,44}?)\s*:\s*$")
_MONTHS = {
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec",
}
_CURRENCIES = {"USD", "EUR", "GBP", "AED", "SAR", "INR", "QAR", "KWD", "BHD", "OMR", "JPY", "CNY"}
_AMOUNT_CCY = re.compile(r"^\s*([A-Z]{3})\s+[\d,]+(?:\.\d+)?\s*$|^\s*[\d,]+(?:\.\d+)?\s+([A-Z]{3})\s*$")
_AR_MARKS = re.compile(r"[\u0640\u064B-\u065F\u0670]")

# English + Arabic labels -> the canonical field names the schemas and rules use.
_LABEL_MAP = {
    "gstin tax id": "gstin", "grn no": "grn_number", "grn number": "grn_number",
    "po reference": "po_number", "po ref": "po_number", "order date": "po_date",
    "order value": "grand_total", "invoice amount": "grand_total", "receipt date": "grn_date",
    "رقم كشف الحساب": "statement_no", "صاحب الحساب": "account_holder", "فترة الكشف": "statement_period",
    "العملة": "currency", "الرصيد الافتتاحي": "opening_balance", "الرصيد الختامي": "closing_balance",
    "رقم الشهادة": "certificate_number", "المصدر": "exporter", "بلد الوجهة": "destination_country",
    "وصف البضائع": "goods_description", "بلد المنشا": "country_of_origin", "تاريخ الاصدار": "issue_date",
    "رقم الفاتورة": "invoice_number", "البائع": "exporter", "المشتري": "buyer",
    "تاريخ الفاتورة": "invoice_date", "اجمالي المبلغ": "grand_total",
    "رقم الاقرار": "declaration_no", "المقر": "declarant", "نوع الاقرار": "declaration_type",
    "البضائع": "goods", "رمز النظام المنسق": "hs_code", "القيمة المصرح بها": "declared_value",
    "الجهة الجمركية": "customs_authority", "تاريخ الاقرار": "declaration_date",
    "الكيان المسجل": "registered_entity", "رقم gst الرقم الضريبي": "gstin",
    "النشاط التجاري": "business_activity", "الدولة": "country",
    "رقم اشعار الاستلام": "grn_number", "المستلم": "receiver", "المورد": "vendor",
    "تاريخ الاستلام": "grn_date", "مرجع امر الشراء": "po_number", "الكمية المستلمة": "quantity_received",
    "حالة الفحص": "inspection_status", "رقم بوليصة الشحن الجوي": "hawb_number", "الشاحن": "shipper",
    "المرسل اليه": "consignee", "الوجهة": "destination", "الوزن الاجمالي": "gross_weight",
    "رقم امر الشراء": "po_number", "تاريخ الطلب": "po_date", "قيمة الطلب": "grand_total",
    "الوصف": "description", "العميل": "customer", "قيمة الفاتورة": "grand_total",
    "شروط الدفع": "payment_terms", "رمز hs": "hs_code", "الكمية": "quantity",
    "سعر الوحدة": "unit_price", "المبلغ": "amount",
}
_LABEL_MAP_BY_TYPE = {
    DocumentType.HOUSE_AIR_WAYBILL: {
        "origin": "airport_of_departure", "destination": "airport_of_destination",
        "المصدر": "airport_of_departure", "الوجهة": "airport_of_destination",
    },
}

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


def _norm_label(label: str) -> str:
    s = _AR_MARKS.sub("", (label or "").lower())
    s = s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    s = re.sub(r"[^\w\s]", " ", s).replace("_", " ")
    return re.sub(r"\s+", " ", s).strip()


def _key(label: str, doc_type: DocumentType | None = None) -> str:
    """Canonical field name; unmapped Arabic labels are kept verbatim."""
    norm = _norm_label(label)
    mapped = _LABEL_MAP_BY_TYPE.get(doc_type, {}).get(norm) or _LABEL_MAP.get(norm)
    if mapped:
        return mapped
    k = _normalize_key(label)
    if not k or re.search(r"[\u0600-\u06FF]", label or ""):
        k = re.sub(r"\s+", " ", (label or "").strip())
    return k


def _display_label(label: str) -> str | None:
    """Arabic labels are shown as written; English keys keep their existing display."""
    label = (label or "").strip()
    return label if re.search(r"[\u0600-\u06FF]", label) else None


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.split("|") if c.strip()] if "|" in line else []


def _clean_lines(text: str) -> list[str]:
    return [ln.strip() for ln in (text or "").splitlines() if ln.strip()]


def extract_fields_from_text(text: str, doc_type: DocumentType) -> dict[str, Field]:
    lines = _clean_lines(text)
    fields: dict[str, Field] = {}

    def add(label: str, value: str, conf: float = 0.97) -> None:
        key = _key(label, doc_type)
        val = (value or "").strip()
        # Drop a redundant leading label echoed into the value ("Opening Balance 125" ->).
        if val.lower().startswith(label.strip().lower()):
            val = val[len(label.strip()):].strip(" :|-")
        if key and val and key not in fields and 0 < len(val) <= 180:
            fields[key] = Field(name=key, value=val, confidence=conf, label=_display_label(label))

    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        cells = _cells(line)

        # Table rows: two cells are a key/value pair; wider rows are line items.
        if cells:
            if len(cells) == 2:
                add(cells[0], cells[1])
            i += 1
            continue

        m = _INLINE_KV.match(line)
        if m and m.group(2).strip():
            add(m.group(1), m.group(2))
            i += 1
            continue

        # "Label:" with its value on the next line.
        m = _TRAILING_COLON.match(line)
        if m and i + 1 < n and not _TRAILING_COLON.match(lines[i + 1]):
            add(m.group(1), lines[i + 1])
            i += 2
            continue

        m = _LABEL_NUM.match(line)
        if m and m.group(1).split()[-1].lower() not in _MONTHS:
            add(m.group(1), m.group(2))
            i += 1
            continue

        m = _SPACED_KV.match(line)
        if m:
            add(m.group(1), m.group(2))
            i += 1
            continue

        # Stacked: a known label on its own line, value on the next (never the title line).
        if i > 0 and i + 1 < n and _is_known_label(line):
            nxt = lines[i + 1]
            if not _is_known_label(nxt):
                add(line, nxt)
                i += 2
                continue
        i += 1

    # A currency written inside the total ("USD 24,850.00") also fills `currency`.
    if "currency" not in fields and "grand_total" in fields:
        m = _AMOUNT_CCY.match(str(fields["grand_total"].value))
        code = m and (m.group(1) or m.group(2))
        if code in _CURRENCIES:
            fields["currency"] = Field(name="currency", value=code, confidence=fields["grand_total"].confidence)

    # Schema order first, then any extra discovered fields.
    names = header_field_names(doc_type)
    ordered: dict[str, Field] = {}
    for k in names:
        if k in fields:
            ordered[k] = fields.pop(k)
    ordered.update(fields)
    return ordered


def _pipe_table(lines: list[str], doc_type: DocumentType) -> tuple[list[str], list[LineItem]]:
    """Line items from a 'col | col | col' grid (DOCX tables and PDF tables)."""
    rows = [_cells(ln) for ln in lines]
    rows = [r for r in rows if len(r) >= 3]
    if len(rows) < 2:
        return [], []
    header, body = rows[0], [r for r in rows[1:] if len(r) == len(rows[0])]
    columns = [_key(h, doc_type) or f"col_{i + 1}" for i, h in enumerate(header)]
    labels = [_display_label(h) for h in header]
    items = []
    for r in body:
        li_fields: dict[str, Field] = {}
        for i, cell in enumerate(r):
            name = columns[i] if columns[i] not in li_fields else f"{columns[i]}_{i + 1}"
            li_fields[name] = Field(name=name, value=cell, confidence=0.97, label=labels[i])
        items.append(LineItem(fields=li_fields))
    return columns, items


def _squash(s: object) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip().casefold()


def locate_values(fields: dict[str, Field], line_items: list[LineItem], full_text: list[TextLine], boxes: list) -> None:
    """Attach page-1 positions to values: exact cell/line first, then 'Label: value' lines."""
    if not boxes:
        return
    entries = [(_squash(t), BoundingBox(page=0, x=b[0], y=b[1], width=b[2] - b[0], height=b[3] - b[1])) for t, b in boxes]
    used: set[int] = set()

    def find(value: object, consume: bool) -> BoundingBox | None:
        v = _squash(value)
        if not v:
            return None
        tests = (lambda t: t == v, lambda t: t.endswith(v), lambda t: v in t) if len(v) >= 3 else (lambda t: t == v,)
        for test in tests:
            hits = [i for i, (t, _) in enumerate(entries) if test(t)]
            if not hits:
                continue
            free = [i for i in hits if i not in used] or hits
            best = min(free, key=lambda i: len(entries[i][0]))
            if consume:
                used.add(best)
            return entries[best][1]
        return None

    for li in line_items:
        for f in li.fields.values():
            f.bbox = find(f.value, consume=True)
    for f in fields.values():
        f.bbox = find(f.value, consume=False)
    for ln in full_text:
        ln.bbox = find(ln.text.split("|")[0], consume=False) if "|" in ln.text else find(ln.text, consume=False)


class TextExtractor(Extractor):
    name = "text"

    def extract(self, raw: RawDocument, doc_type: DocumentType) -> Extraction:
        text = raw.text
        lines = _clean_lines(text)

        fields = extract_fields_from_text(text, doc_type)

        table_columns, line_items = _pipe_table(lines, doc_type)
        if not line_items:
            # Detect a simple table from any 3+ column spaced rows.
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

        locate_values(fields, line_items, full_text, raw.pages[0].boxes if raw.pages else [])

        if raw.kind:
            source = "pdf" if raw.kind == "pdf" else "docx/text"
        else:
            source = "pdf" if (raw.content_type == "image/png" or (raw.name or "").lower().endswith(".pdf")) else "docx/text"
        return Extraction(
            doc_type=doc_type,
            engine=f"text:{source}" if lines else "unreadable",
            fields=fields,
            line_items=line_items,
            full_text=full_text,
            table_columns=table_columns,
        )
