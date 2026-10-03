"""LLM-backed extractor (stub for the real product path).

The production flow is:
  1. Run OCR/layout (Azure Document Intelligence / AWS Textract / Google Document AI,
     or self-hosted PaddleOCR + LayoutLMv3) to get text + word bounding boxes.
  2. Send text + layout + the target JSON schema to a vision/LLM with structured output.
  3. Map returned values back to their source spans to populate bounding boxes.

Wire up your provider credentials via .env (LLM_* settings) and implement `extract`.
Kept as a NotImplementedError stub so the POC stays runnable without any API keys.
"""
from __future__ import annotations

from ..config import settings
from ..models import DocumentType, Extraction
from .base import Extractor, RawDocument


class LLMExtractor(Extractor):
    name = "llm"

    def extract(self, raw: RawDocument, doc_type: DocumentType) -> Extraction:
        if not settings.llm_api_key:
            raise RuntimeError(
                "EXTRACTOR=llm requires LLM_* settings. Set them in your local env "
                "(never commit secrets) or use EXTRACTOR=mock for offline demos."
            )
        raise NotImplementedError(
            "Implement provider call here: OCR -> prompt with schema -> structured "
            "JSON -> map values to source bounding boxes."
        )
