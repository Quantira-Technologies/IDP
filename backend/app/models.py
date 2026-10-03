"""Domain models shared across the pipeline.

Every extracted value is a `Field` that carries its own confidence and a
`BoundingBox` pointing back to the exact spot on the page it came from — this is
what makes the "100% of fields traced to source" promise concrete.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field as PydField


class Workflow(str, Enum):
    """A business area. Each runs the same six-step pipeline, configured with the
    document types and rulesets specific to its own documents."""

    CUSTOMS = "customs"
    PO2PAY = "po2pay"
    CONTRACTS = "contracts"
    FINANCE = "finance"
    UNKNOWN = "unknown"


class DocumentType(str, Enum):
    # Customs Clearance
    COMMERCIAL_INVOICE = "commercial_invoice"
    CERTIFICATE_OF_ORIGIN = "certificate_of_origin"
    HOUSE_AIR_WAYBILL = "house_air_waybill"
    CUSTOMS_DECLARATION = "customs_declaration"
    # Po2Pay
    PURCHASE_ORDER = "purchase_order"
    GOODS_RECEIPT_NOTE = "goods_receipt_note"
    VENDOR_INVOICE = "vendor_invoice"
    # Contract Management
    GST_CERTIFICATE = "gst_certificate"
    # Finance Operations
    BANK_STATEMENT = "bank_statement"
    UNKNOWN = "unknown"


#: Which workflow each document type belongs to.
WORKFLOW_OF: dict["DocumentType", Workflow] = {
    DocumentType.COMMERCIAL_INVOICE: Workflow.CUSTOMS,
    DocumentType.CERTIFICATE_OF_ORIGIN: Workflow.CUSTOMS,
    DocumentType.HOUSE_AIR_WAYBILL: Workflow.CUSTOMS,
    DocumentType.CUSTOMS_DECLARATION: Workflow.CUSTOMS,
    DocumentType.PURCHASE_ORDER: Workflow.PO2PAY,
    DocumentType.GOODS_RECEIPT_NOTE: Workflow.PO2PAY,
    DocumentType.VENDOR_INVOICE: Workflow.PO2PAY,
    DocumentType.GST_CERTIFICATE: Workflow.CONTRACTS,
    DocumentType.BANK_STATEMENT: Workflow.FINANCE,
}


def workflow_of(doc_type: "DocumentType") -> Workflow:
    return WORKFLOW_OF.get(doc_type, Workflow.UNKNOWN)


class RouteDecision(str, Enum):
    AUTO_APPROVED = "auto_approved"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"


class RuleSeverity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"


class BoundingBox(BaseModel):
    """Normalized (0-1) coordinates so the UI can overlay on any render size."""

    page: int = 0
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0


class Field(BaseModel):
    name: str
    value: Any = None
    confidence: float = 0.0
    bbox: BoundingBox | None = None
    # Set true once a human corrects/approves the value in review.
    corrected: bool = False


class LineItem(BaseModel):
    fields: dict[str, Field] = PydField(default_factory=dict)


class TextLine(BaseModel):
    """A single OCR'd line — used for the full, verbatim document capture."""

    text: str
    confidence: float = 0.0
    bbox: BoundingBox | None = None


class QRCode(BaseModel):
    """A QR/barcode found on the page — decoded value + a cropped snapshot."""

    data: str
    bbox: BoundingBox | None = None
    image: str | None = None  # base64 data URL of the cropped code


class Extraction(BaseModel):
    doc_type: DocumentType
    engine: str
    fields: dict[str, Field] = PydField(default_factory=dict)
    line_items: list[LineItem] = PydField(default_factory=list)
    # Verbatim capture of every line on the page (source-traced).
    full_text: list[TextLine] = PydField(default_factory=list)
    # Any QR / matrix codes detected, snapshotted and decoded separately.
    qr_codes: list[QRCode] = PydField(default_factory=list)
    # Header for a detected table (bill of materials / line-item grid).
    table_columns: list[str] = PydField(default_factory=list)

    def min_confidence(self) -> float:
        scores = [f.confidence for f in self.fields.values()]
        for li in self.line_items:
            scores.extend(f.confidence for f in li.fields.values())
        return min(scores) if scores else 0.0


class RuleResult(BaseModel):
    rule_id: str
    description: str
    severity: RuleSeverity
    passed: bool
    detail: str = ""


class SubDocumentResult(BaseModel):
    index: int
    doc_type: DocumentType
    workflow: Workflow = Workflow.UNKNOWN
    engine: str
    extraction: Extraction
    rule_results: list[RuleResult] = PydField(default_factory=list)
    min_confidence: float = 0.0
    route: RouteDecision = RouteDecision.NEEDS_REVIEW
    route_reasons: list[str] = PydField(default_factory=list)


class DocumentResult(BaseModel):
    id: str
    source_name: str
    image_url: str | None = None
    sub_documents: list[SubDocumentResult] = PydField(default_factory=list)
    # Ownership & organization (set when saved).
    owner: str | None = None
    created_at: str | None = None
    folder_id: str | None = None
    approved: bool = False


class CorrectionRequest(BaseModel):
    """A reviewer correcting a field value and (optionally) approving the sub-doc."""

    sub_index: int
    field_name: str
    new_value: Any
    approve: bool = False
