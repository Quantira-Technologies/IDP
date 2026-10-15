"""Business-rule engine.

Rules are the intel2doc differentiator: they test whether a value is *factually
right* against your business logic, not merely whether OCR read it correctly.

A rule is a callable that receives the sub-document context and returns a
`RuleResult`. Cross-document rules (e.g. Certificate of Origin -> Invoice match)
receive the sibling extractions in the same bundle.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Callable

from ..models import Extraction, RuleResult, RuleSeverity

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def load_hs_rates() -> dict:
    with open(os.path.join(_DATA_DIR, "hs_code_rates.json"), encoding="utf-8") as fh:
        return json.load(fh)


@dataclass
class RuleContext:
    extraction: Extraction
    siblings: list[Extraction]  # other sub-documents in the same bundle
    hs_rates: dict


Rule = Callable[[RuleContext], RuleResult]


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
_UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19,
}
_TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
    "seventy": 70, "eighty": 80, "ninety": 90,
}
_SCALES = {"hundred": 100, "thousand": 1000, "million": 1_000_000}


def words_to_number(text: str) -> float | None:
    """Convert an English amount phrase to a number.

    Handles the common invoice pattern "<whole> AND CENTS <fraction>".
    Returns None if it cannot parse.
    """
    if not text:
        return None
    text = text.lower().replace("-", " ").replace(",", " ")
    text = re.sub(r"\b(u\.?s\.?|dollars?|only|and)\b", " ", text)

    cents_part = None
    m = re.search(r"cents?\s+(.*)$", text)
    if m:
        cents_words = m.group(1)
        text = text[: m.start()]
        cents_part = _phrase_to_int(cents_words)

    whole = _phrase_to_int(text)
    if whole is None:
        return None
    total = float(whole)
    if cents_part is not None:
        total += cents_part / 100.0
    return total


def _phrase_to_int(text: str) -> int | None:
    tokens = [t for t in re.split(r"\s+", text.strip()) if t]
    if not tokens:
        return None
    current = 0
    total = 0
    matched = False
    for tok in tokens:
        if tok in _UNITS:
            current += _UNITS[tok]
            matched = True
        elif tok in _TENS:
            current += _TENS[tok]
            matched = True
        elif tok == "hundred":
            current = (current or 1) * 100
            matched = True
        elif tok in _SCALES:
            total += (current or 1) * _SCALES[tok]
            current = 0
            matched = True
        # ignore unknown tokens
    return total + current if matched else None


_AMOUNT_WITH_UNIT = re.compile(r"(?:[A-Za-z\u0600-\u06FF]{1,4}\s*)?(-?\d+(?:\.\d+)?)\s*(?:[A-Za-z\u0600-\u06FF]{1,6})?")


def _num(value) -> float | None:
    text = str(value).replace(",", "").strip()
    try:
        return float(text)
    except (TypeError, ValueError):
        # Accept a currency code or unit next to the number ("USD 24850.00", "1250 KG").
        m = _AMOUNT_WITH_UNIT.fullmatch(text)
        return float(m.group(1)) if m else None


# GSTIN checksum (India). 15 chars: 2 state + 10 PAN + 1 entity + 'Z' + 1 check.
_GST_CHARSET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def gstin_check_digit(first_14: str) -> str | None:
    """Return the expected 15th (check) character for the first 14 GSTIN chars."""
    if len(first_14) != 14 or any(c not in _GST_CHARSET for c in first_14):
        return None
    factor = 2
    total = 0
    cp = len(_GST_CHARSET)
    for ch in reversed(first_14):
        digit = factor * _GST_CHARSET.index(ch)
        factor = 1 if factor == 2 else 2
        digit = digit // cp + digit % cp
        total += digit
    return _GST_CHARSET[(cp - (total % cp)) % cp]


def is_valid_gstin(gstin: str) -> bool:
    if not gstin or len(gstin) != 15:
        return False
    expected = gstin_check_digit(gstin[:14])
    return expected is not None and expected == gstin[14]
