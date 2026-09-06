#!/usr/bin/env python3
"""Move a superseded artifact to a preserved audit location."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--reason", required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"output exists: {args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(args.source), str(args.output))
    receipt = args.output.with_suffix(args.output.suffix + ".preservation.json")
    receipt.write_text(json.dumps({"schema_version": 1, "source": str(args.source),
                                   "preserved_as": str(args.output), "reason": args.reason}, indent=2) + "\n",
                       encoding="utf-8")
    print(json.dumps({"preserved_as": str(args.output), "reason": args.reason}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
