"""Step 3 — Select: pick the best extraction engine for this document type.

POC returns the single configured extractor. Production routes per document type
(e.g. a table-optimized model for invoices, a clause model for contracts) and can
fall back between engines on low confidence.
"""
from __future__ import annotations

from ..extractors.base import Extractor, RawDocument, get_extractor
from ..models import DocumentType


def select_engine(doc_type: DocumentType, raw: RawDocument | None = None) -> Extractor:
    return get_extractor(raw)
