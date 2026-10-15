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
    if not text_source.strip() and raw.has_image and settings.extractor != "ollama":
        try:
            from ..extractors.ocr_extractor import available, ocr_text

            if available():
                text = ocr_text(raw.image_bytes)
                if text.strip():
                    text_source = text
        except Exception:
            pass

    text = text_source.upper()
    # --- Arabic keyword checks (case-insensitive upper() leaves Arabic intact) ---
    # Specific titles first: GRN / vendor invoices also mention a purchase order.
    if "إشعار استلام" in text_source or "إشعار الاستلام" in text_source:
        return DocumentType.GOODS_RECEIPT_NOTE
    if "فاتورة المورد" in text_source or "فاتورة مورد" in text_source:
        return DocumentType.VENDOR_INVOICE
    if "شهادة منشأ" in text_source or "بلد المنشأ" in text_source:
        return DocumentType.CERTIFICATE_OF_ORIGIN
    if "بوليصة شحن جوي" in text_source:
        return DocumentType.HOUSE_AIR_WAYBILL
    if "كشف حساب" in text_source or "كشف الحساب" in text_source or "بيان حساب" in text_source:
        return DocumentType.BANK_STATEMENT
    if "إقرار جمركي" in text_source or "بيان جمركي" in text_source:
        return DocumentType.CUSTOMS_DECLARATION
    if "شهادة ضريبة" in text_source:
        return DocumentType.GST_CERTIFICATE
    if "فاتورة تجارية" in text_source:
        return DocumentType.COMMERCIAL_INVOICE
    if "أمر شراء" in text_source:
        return DocumentType.PURCHASE_ORDER
    # Customs Clearance
    if "CERTIFICATE OF ORIGIN" in text or "ORIGIN CRITERION" in text or "COUNTRY OF ORIGIN" in text:
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
