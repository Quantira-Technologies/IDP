"""Extractor interface + factory.

An extractor turns a raw (OCR'd) document into an `Extraction` where every field
carries a confidence score and a bounding box. Swapping mock <-> llm <-> a future
Document-AI extractor changes nothing downstream.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field

from ..config import settings
from ..models import DocumentType, Extraction


@dataclass
class RawPage:
    number: int
    text: str


@dataclass
class RawDocument:
    """A (possibly multi-page) document after ingestion/OCR.

    In production `text` comes from an OCR/layout engine. In this POC it is canned
    sample content so the pipeline is fully runnable offline. When a real image is
    uploaded, `image_bytes` holds the original bytes so the vision extractor
    (Ollama) can read directly from the page.
    """

    name: str
    pages: list[RawPage] = field(default_factory=list)
    image_bytes: bytes | None = None
    content_type: str | None = None

    @property
    def text(self) -> str:
        return "\n".join(p.text for p in self.pages)

    @property
    def has_image(self) -> bool:
        return self.image_bytes is not None and len(self.image_bytes) > 0


class Extractor(abc.ABC):
    name: str = "base"

    @abc.abstractmethod
    def extract(self, raw: RawDocument, doc_type: DocumentType) -> Extraction:
        ...


def get_extractor(raw: "RawDocument | None" = None) -> Extractor:
    """Factory driven by the EXTRACTOR env setting (image-aware).

    - "ollama"      → vision LLM (needs an image + a running Ollama server)
    - "ollama_text" → OCR (Tesseract) then a text chat model (e.g. qwen2.5:1.5b)
    - "ocr"         → Tesseract OCR for images
    - "auto"        → OCR when an image is present and Tesseract is installed, else mock
    - "mock"        → offline deterministic sample data (default)
    """
    mode = settings.extractor
    has_image = raw is not None and raw.has_image

    if mode == "ollama":
        from .ollama_extractor import OllamaExtractor

        return OllamaExtractor()
    if mode == "ollama_text":
        from .ollama_text_extractor import OllamaTextExtractor

        return OllamaTextExtractor()
    if mode == "llm":
        from .llm_extractor import LLMExtractor

        return LLMExtractor()
    if mode in ("ocr", "auto") and has_image:
        from .ocr_extractor import OCRExtractor, available

        if available():
            return OCRExtractor()
        # "ocr" explicitly requested but Tesseract missing → fall back to mock.
    from .mock_extractor import MockExtractor

    return MockExtractor()
