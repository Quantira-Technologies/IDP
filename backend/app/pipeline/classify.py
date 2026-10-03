"""Step 1 — Classify: what document is this?

POC uses keyword heuristics over the OCR text. When a real image is uploaded and
the Ollama vision extractor is active, the image itself is classified by the
model. Production uses a trained document-type classifier with a confidence score.
"""
from __future__ import annotations

from ..config import settings
from ..extractors.base import RawDocument
from ..models import DocumentType


def classify(raw: RawDocument) -> DocumentType:
    # Vision path: let the multimodal model classify the image directly.
    if settings.extractor == "ollama" and raw.has_image:
        from ..extractors import ollama_client
        from ..extractors.ollama_extractor import classify_prompt, parse_doc_type

        try:
            response = ollama_client.generate_vision(classify_prompt(), raw.image_bytes)
            doc_type = parse_doc_type(response)
            if doc_type != DocumentType.UNKNOWN:
                return doc_type
        except Exception:
            # Fall through to text heuristics (e.g. Ollama unreachable).
            pass

    # OCR path: read the image text so keyword classification works on real uploads.
    text_source = raw.text
    if settings.extractor in ("ocr", "auto") and raw.has_image:
        try:
            from ..extractors.ocr_extractor import available, ocr_text

            if available():
                text = ocr_text(raw.image_bytes)
                if text.strip():
                    text_source = text
        except Exception:
            pass

    text = text_source.upper()
    # Customs Clearance
    if "CERTIFICATE OF ORIGIN" in text or "ORIGIN CRITERION" in text:
        return DocumentType.CERTIFICATE_OF_ORIGIN
    if "AIR WAYBILL" in text or "HAWB" in text or "HOUSE AIR WAYBILL" in text:
        return DocumentType.HOUSE_AIR_WAYBILL
    if "CUSTOMS DECLARATION" in text or "TRAVELER INFORMATION" in text or "SAUDI CUSTOMS" in text:
        return DocumentType.CUSTOMS_DECLARATION
    # Contract Management
    if "GST" in text and ("REGISTRATION CERTIFICATE" in text or "GSTIN" in text):
        return DocumentType.GST_CERTIFICATE
    # Finance Operations
    if "BANK STATEMENT" in text or "STATEMENT OF ACCOUNT" in text or "RUNNING BALANCE" in text:
        return DocumentType.BANK_STATEMENT
    # Po2Pay
    if "GOODS RECEIPT" in text or "GRN" in text:
        return DocumentType.GOODS_RECEIPT_NOTE
    if "PURCHASE ORDER" in text or text.lstrip().startswith("PO "):
        return DocumentType.PURCHASE_ORDER
    if "VENDOR INVOICE" in text or "TAX INVOICE" in text or "SUPPLIER INVOICE" in text:
        return DocumentType.VENDOR_INVOICE
    if "INVOICE" in text or "COMMERCIAL INVOICE" in text:
        return DocumentType.COMMERCIAL_INVOICE
    return DocumentType.UNKNOWN
