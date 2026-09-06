#!/usr/bin/env python3
"""Tighten candidate-01 guards after its development-only precision check."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"output exists: {args.output}")
    shutil.copytree(args.candidate, args.output)
    classifier = args.output / "classify.py"
    source = classifier.read_text(encoding="utf-8")
    source = source.replace('(\"Notices\", r\"\\bnotices?\\b\")',
                            '(\"Notices\", r\"\\ball notices\\b|\\bnotice shall be\\b|\\bnotices shall be\\b\")')
    source = source.replace('(\"Survival\", r\"\\bsurviv(?:e|es|ed|al)\\b|\\brepayment satisfaction or discharge\\b\")',
                            '(\"Survival\", r\"\\bshall survive (?:the )?(?:closing|termination|expiration|resignation)\\b|\\brepayment satisfaction or discharge\\b\")')
    classifier.write_text(source, encoding="utf-8")
    construction_path = args.output / "construction.json"
    construction = json.loads(construction_path.read_text(encoding="utf-8"))
    construction.update({
        "candidate_id": "candidate-02",
        "parent_candidate_id": "candidate-01",
        "hypothesis": "Requiring notice-delivery language and explicit survival events removes cross-reference false positives while retaining conservative local coverage.",
    })
    construction_path.write_text(json.dumps(construction, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"candidate": "candidate-02", "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
