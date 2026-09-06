#!/usr/bin/env python3
"""Restrict CFPB candidate-01 to its high-precision development routes."""

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
    start = source.index("RULES = (")
    end = source.index("\n\n\ndef classify", start)
    rules = '''RULES = (
    ("Prepaid card", r"\\bprepaid (?:debit |gift )?card\\b|\\b(?:vanilla|incomm)\\b.{0,80}\\b(?:visa|card)\\b|\\bvisa gift card\\b"),
    ("Student loan", r"\\bstudent loans?\\b|\\b(?:mohela|navient|nelnet)\\b|\\bdepartment of education\\b.{0,100}\\bloans?\\b"),
    ("Mortgage", r"\\bmortgage\\b|\\bforeclosure\\b|\\bhome equity line of credit\\b|\\bheloc\\b|\\bescrow account\\b"),
    ("Payday loan, title loan, personal loan, or advance loan", r"\\b(?:payday|title|personal|advance) loans?\\b|\\baffirm\\b"),
)'''
    classifier.write_text(source[:start] + rules + source[end:], encoding="utf-8")
    construction_path = args.output / "construction.json"
    construction = json.loads(construction_path.read_text(encoding="utf-8"))
    construction.update({"candidate_id": "candidate-02", "parent_candidate_id": "candidate-01",
                         "hypothesis": "Restrict routing to four product patterns with at least 94.9 percent observed development precision; all other narratives fall back."})
    construction_path.write_text(json.dumps(construction, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"candidate": "candidate-02", "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
