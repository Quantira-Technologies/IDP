"""Step 2 — Segment: split a bundle into individual sub-documents.

A single upload can contain many stacked documents (e.g. 15 invoices, or an
invoice + its certificate of origin). Each sub-document then runs the remaining
steps independently.

POC boundary detection uses an explicit page marker. Production would detect
boundaries via the classifier + layout signals (new header, page-1 patterns).
"""
from __future__ import annotations

from ..extractors.base import RawDocument, RawPage

BUNDLE_DELIMITER = "<<<DOC-BOUNDARY>>>"


def segment(raw: RawDocument) -> list[RawDocument]:
    # A single uploaded image is one document (no text boundaries to split on).
    if raw.has_image:
        return [raw]

    # If any page contains the boundary marker, split on it.
    joined = raw.text
    if BUNDLE_DELIMITER not in joined:
        return [raw]

    sub_docs: list[RawDocument] = []
    current: list[str] = []
    idx = 0
    for chunk in joined.split(BUNDLE_DELIMITER):
        chunk = chunk.strip()
        if not chunk:
            continue
        idx += 1
        sub_docs.append(
            RawDocument(name=f"{raw.name}#part{idx}", pages=[RawPage(number=0, text=chunk)])
        )
    return sub_docs or [raw]
