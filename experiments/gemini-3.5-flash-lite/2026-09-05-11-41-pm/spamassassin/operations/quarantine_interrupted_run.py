#!/usr/bin/env python3
"""Preserve an interrupted partial run outside the promotable result namespace."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--partial", required=True, type=Path)
    parser.add_argument("--attempts", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"output exists: {args.output}")
    if not args.partial.is_file() or not args.attempts.is_dir():
        raise SystemExit("interrupted partial run is incomplete")
    args.output.mkdir(parents=True)
    shutil.move(str(args.partial), args.output / args.partial.name)
    shutil.move(str(args.attempts), args.output / args.attempts.name)
    receipt = {
        "schema_version": 1,
        "status": "preserved_interrupted",
        "reason": "transient hosted connection error",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "partial": args.partial.name,
        "attempts": args.attempts.name,
    }
    (args.output / "quarantine.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
