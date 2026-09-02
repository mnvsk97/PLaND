#!/usr/bin/env python3
"""Return bounded OCR text plus deterministic structural metadata."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = PROJECT_ROOT / "data" / "manifest.json"
MAX_INPUT_CHARS = 200_000
MAX_OUTPUT_TEXT_CHARS = 3_200
HEAD_CHARS = 2_200
TAIL_CHARS = 900


def compact(text: str) -> dict[str, object]:
    normalized = re.sub(r"\n{3,}", "\n\n", text.replace("\r\n", "\n").replace("\r", "\n"))
    truncated = len(normalized) > MAX_OUTPUT_TEXT_CHARS
    excerpt = normalized
    if truncated:
        excerpt = normalized[:HEAD_CHARS].rstrip() + "\n\n[...middle omitted...]\n\n" + normalized[-TAIL_CHARS:].lstrip()
    lines = [line.strip() for line in normalized.splitlines() if line.strip()]
    return {
        "source_characters": len(text),
        "source_lines": len(lines),
        "short_line_ratio": round(sum(len(line) <= 40 for line in lines) / len(lines), 3) if lines else 0,
        "currency_symbol_count": sum(normalized.count(symbol) for symbol in ("$", "€", "£")),
        "question_mark_count": normalized.count("?"),
        "truncated": truncated,
        "text": excerpt,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True)
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    approved = {item["path"] for item in manifest["sources"]}
    normalized = Path(args.file).as_posix().lstrip("/")
    if normalized not in approved:
        raise SystemExit(f"datasource is not approved: {args.file}")
    text = (Path(manifest["datasource_root"]) / normalized).read_text(encoding="utf-8", errors="replace")
    if len(text) > MAX_INPUT_CHARS:
        raise SystemExit(f"datasource exceeds {MAX_INPUT_CHARS} characters: {normalized}")
    print(json.dumps(compact(text), separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
