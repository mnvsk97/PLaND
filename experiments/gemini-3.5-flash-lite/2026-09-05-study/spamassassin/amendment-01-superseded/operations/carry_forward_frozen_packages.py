#!/usr/bin/env python3
"""Carry forward byte-identical frozen packages into the amended lineage."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def tree_hash(root: Path) -> str:
    items = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        items.append((path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(items, separators=(",", ":")).encode()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"output exists: {args.output}")
    shutil.copytree(args.source, args.output)
    source_hash = tree_hash(args.source)
    output_hash = tree_hash(args.output)
    if source_hash != output_hash:
        raise SystemExit("carried package hash mismatch")
    print(json.dumps({"source": str(args.source), "output": str(args.output),
                      "tree_sha256": output_hash, "byte_identical": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
