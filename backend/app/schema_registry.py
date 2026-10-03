"""Loads the per-document-type field schemas (`app/schemas/*.json`).

These schemas define which header fields and line-item fields each document type
has. The mock extractor mirrors them by hand; the Ollama vision extractor uses
them to build its extraction prompt so adding a new document type is just a new
schema + ruleset — no extractor code changes.
"""
from __future__ import annotations

import functools
import json
import os

from .models import DocumentType

_SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "schemas")


@functools.lru_cache(maxsize=1)
def _all_schemas() -> dict[str, dict]:
    schemas: dict[str, dict] = {}
    if not os.path.isdir(_SCHEMA_DIR):
        return schemas
    for fname in os.listdir(_SCHEMA_DIR):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(_SCHEMA_DIR, fname), encoding="utf-8") as fh:
            data = json.load(fh)
        doc_type = data.get("doc_type")
        if doc_type:
            schemas[doc_type] = data
    return schemas


def get_schema(doc_type: DocumentType) -> dict | None:
    return _all_schemas().get(doc_type.value)


def header_field_names(doc_type: DocumentType) -> list[str]:
    schema = get_schema(doc_type) or {}
    return [f["name"] for f in schema.get("header_fields", [])]


def line_item_field_names(doc_type: DocumentType) -> list[str]:
    schema = get_schema(doc_type) or {}
    return [f["name"] for f in schema.get("line_item_fields", [])]
