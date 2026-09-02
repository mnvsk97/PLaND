#!/usr/bin/env python3
"""Return a deterministic bounded head/tail view of approved OCR text."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LIMIT = 1_600
HEAD = 1_150
TAIL = 400


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True)
    args = parser.parse_args()
    manifest = json.loads((ROOT / "data" / "manifest.json").read_text(encoding="utf-8"))
    approved = {item["path"] for item in manifest["sources"]}
    normalized = Path(args.file).as_posix().lstrip("/")
    if normalized not in approved:
        raise SystemExit(f"datasource is not approved: {args.file}")
    text = (Path(manifest["datasource_root"]) / normalized).read_text(encoding="utf-8", errors="replace")
    if len(text) > LIMIT:
        text = text[:HEAD].rstrip() + "\n[...middle omitted...]\n" + text[-TAIL:].lstrip()
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
