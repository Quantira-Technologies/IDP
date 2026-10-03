"""Sample ingestion for the POC.

Real ingestion runs OCR/layout over the uploaded bytes. Here we synthesize the
OCR text so the pipeline is fully runnable offline:

  * `raw_from_upload` — inspects the filename to pick a canned document, so a real
    upload still flows through the whole pipeline.
  * `demo_bundle` — a single "PDF" containing a commercial invoice AND its
    certificate of origin, separated by a boundary marker, to demonstrate
    bundle-splitting + cross-document validation.
"""
from __future__ import annotations

from .extractors.base import RawDocument, RawPage
from .pipeline.segment import BUNDLE_DELIMITER

_INVOICE_TEXT = """COMMERCIAL INVOICE
No. HCM20150907GDY  Date SEP 07 2015
Shipped per CAPE FELTON V-15010N
To GDYNIA, POLAND
PO# 4500280268
Marks Quantity Description Unit Price Amount HS Code Duty
STEEL DROP IN ANCHOR ZPCR6+ M8X10X30 78000 PCS USD 29.33 USD 2287.74
M10X12X40 47000 PCS USD 44.54 USD 2093.38
TOTAL 125000 PCS USD 4381.12
SAY TOTAL U.S. DOLLARS FOUR THOUSAND THREE HUNDRED EIGHTY ONE AND CENTS TWELVE ONLY
"""

_COO_TEXT = """CERTIFICATE OF ORIGIN
Asia-Pacific Trade Agreement (Combined Declaration and Certificate)
Certificate No 01251110720001256
Goods consigned from NINGBO FASTENER MFG CO., LTD
Goods consigned to GDYNIA, POLAND
Country of origin CHINA
Number and date of invoices HCM20150907GDY SEP 07 2015
Tariff item 7318.15.00 STEEL DROP IN ANCHOR ZPCR6+
Origin criterion A  Gross weight 3162 KGS
"""

# --- Po2Pay workflow ------------------------------------------------------- #
_PO_TEXT = """PURCHASE ORDER
PO No PO-88231  Date 2026-08-01
Vendor ACME STEEL WORKS LTD
SKU ANC-M8  DROP-IN ANCHOR M8  Qty 100  Unit 20.00  Amount 2000.00
SKU ANC-M10 DROP-IN ANCHOR M10 Qty 100  Unit 30.00  Amount 3000.00
Total USD 5000.00
"""

_GRN_TEXT = """GOODS RECEIPT NOTE (GRN)
GRN No GRN-55012  Date 2026-08-14
PO No PO-88231  Vendor ACME STEEL WORKS LTD
SKU ANC-M8  Received 100
SKU ANC-M10 Received 90
"""

_VENDOR_INVOICE_TEXT = """TAX INVOICE
Invoice No ACME-INV-7741  Date 2026-08-16
PO No PO-88231  Vendor ACME STEEL WORKS LTD
SKU ANC-M8  Billed 100  Unit 20.00  Amount 2000.00
SKU ANC-M10 Billed 100  Unit 33.00  Amount 3300.00
Total USD 5300.00
"""

# --- Contract Management workflow ------------------------------------------ #
_GST_TEXT = """GOODS AND SERVICES TAX
GST REGISTRATION CERTIFICATE
GSTIN 27AAPFU0939F1ZV
Legal Name USMAN CASHMERE TRADING CO
Trade Name USMAN CASHMERE
State MAHARASHTRA  Registration Date 2019-07-01
Constitution Partnership
"""

# --- Finance Operations workflow ------------------------------------------- #
_BANK_TEXT = """BANK STATEMENT
Statement of Account  Account XXXX-4471  Period 2026-08
Opening Balance 10000.00
2026-08-03 CUSTOMER PAYMENT INV-201  Credit 3000.00  Balance 13000.00
2026-08-11 SUPPLIER PAYMENT ACME     Debit  1250.00  Balance 11750.00
Closing Balance 11750.00
"""

# --- Customs — House Air Waybill & Traveler Declaration -------------------- #
_HAWB_TEXT = """HOUSE AIR WAYBILL  HAWB No MHG00035659
Carrier ETIHAD AIRWAYS  Flight EY 002/08  Terms CIF
Airport of Departure AUH  Airport of Destination BRISBANE
Gross Weight 460 KG  Chargeable Weight 460 KG  Currency EUR
Nature of Goods Laminates, not restricted
"""

_DECLARATION_TEXT = """SAUDI CUSTOMS DECLARATION
Traveler Information
First Name AHMED  Surname AL-QAHTANI  Nationality Saudi
Passport No A1234567  Purpose of Travel Business
Arriving From DUBAI  Departing To RIYADH  Flight EY 512
"""


_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff")


def _is_image(filename: str, content_type: str | None) -> bool:
    if content_type and content_type.startswith("image/"):
        return True
    return (filename or "").lower().endswith(_IMAGE_EXTS)


def _canned_for_filename(filename: str) -> RawDocument:
    """Pick a canned document based on the filename (POC stand-in for OCR text)."""
    lower = (filename or "").lower()
    if "origin" in lower or "coo" in lower or "certificate" in lower:
        if "gst" in lower:
            return RawDocument(name=filename, pages=[RawPage(0, _GST_TEXT)])
        return RawDocument(name=filename, pages=[RawPage(0, _COO_TEXT)])
    if "waybill" in lower or "hawb" in lower or "awb" in lower:
        return RawDocument(name=filename, pages=[RawPage(0, _HAWB_TEXT)])
    if "declaration" in lower or "customs" in lower or "traveler" in lower:
        return RawDocument(name=filename, pages=[RawPage(0, _DECLARATION_TEXT)])
    if "gst" in lower:
        return RawDocument(name=filename, pages=[RawPage(0, _GST_TEXT)])
    if "bank" in lower or "statement" in lower:
        return RawDocument(name=filename, pages=[RawPage(0, _BANK_TEXT)])
    if "grn" in lower or "receipt" in lower:
        return RawDocument(name=filename, pages=[RawPage(0, _GRN_TEXT)])
    if lower.startswith("po") or "purchase" in lower:
        return RawDocument(name=filename, pages=[RawPage(0, _PO_TEXT)])
    if "vendor" in lower or "supplier" in lower:
        return RawDocument(name=filename, pages=[RawPage(0, _VENDOR_INVOICE_TEXT)])
    # Default to a commercial invoice for anything else.
    return RawDocument(name=filename or "commercial_invoice", pages=[RawPage(0, _INVOICE_TEXT)])


def raw_from_upload(
    filename: str, content: bytes, content_type: str | None = None
) -> RawDocument:
    """Build a RawDocument from an upload.

    For images, the raw bytes are attached so the Ollama vision extractor can read
    the page directly. A filename-based canned text is still attached as an offline
    fallback (used by the mock extractor, and by classify if the model is offline).
    """
    doc = _canned_for_filename(filename)
    if _is_image(filename, content_type):
        doc.image_bytes = content
        doc.content_type = content_type or "image/jpeg"
    return doc


def demo_bundle() -> RawDocument:
    text = f"{_INVOICE_TEXT}\n{BUNDLE_DELIMITER}\n{_COO_TEXT}"
    return RawDocument(name="demo_bundle.pdf", pages=[RawPage(0, text)])


def po2pay_bundle() -> RawDocument:
    """Purchase Order + Goods Receipt Note + Vendor Invoice for a three-way match."""
    text = f"{_PO_TEXT}\n{BUNDLE_DELIMITER}\n{_GRN_TEXT}\n{BUNDLE_DELIMITER}\n{_VENDOR_INVOICE_TEXT}"
    return RawDocument(name="po2pay_bundle.pdf", pages=[RawPage(0, text)])


#: Named demo bundles, one per workflow, for the /api/demo/{name} endpoint.
DEMO_BUNDLES = {
    "customs": demo_bundle,
    "po2pay": po2pay_bundle,
    "contracts": lambda: RawDocument(name="gst_certificate.pdf", pages=[RawPage(0, _GST_TEXT)]),
    "finance": lambda: RawDocument(name="bank_statement.pdf", pages=[RawPage(0, _BANK_TEXT)]),
}
