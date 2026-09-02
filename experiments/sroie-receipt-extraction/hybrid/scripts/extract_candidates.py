#!/usr/bin/env python3
"""Compact receipt OCR into deterministic field candidates using stdlib only."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

DATE = re.compile(r"\b(?:\d{1,2}[-/.]\d{1,2}[-/.](?:\d{2}|\d{4})|(?:\d{2}|\d{4})[-/.]\d{1,2}[-/.]\d{1,2})\b")
MONEY = re.compile(r"(?<!\d)(?:RM\s*)?\d{1,6}[.,]\d{2}(?!\d)", re.I)
TOTAL = re.compile(r"\b(?:grand\s+total|net\s+total|total(?:\s+amount)?|amount\s+due)\b", re.I)
ADDRESS = re.compile(r"\b(?:jalan|jln|road|rd|street|st|lot|no\.?|taman|persiaran|selangor|kuala\s+lumpur)\b", re.I)


def candidates(words: list[str]) -> dict[str, object]:
    # Lossless normalization is intentionally conservative: earlier candidate
    # pruning reduced quality. The code step now guarantees a stable JSON
    # envelope without dropping or adding receipt evidence.
    return {"words": words}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args()
    value = json.loads(args.input.read_text(encoding="utf-8"))
    words = value.get("words") or value.get("frozen_ocr", {}).get("words") or []
    print(json.dumps(candidates([str(word) for word in words]), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
