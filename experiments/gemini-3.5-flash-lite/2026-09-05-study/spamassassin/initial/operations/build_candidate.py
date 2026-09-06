#!/usr/bin/env python3
"""Build a conservative SpamAssassin command candidate."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


CLASSIFIER = r'''"""Conservative, standard-library SpamAssassin classifier."""
from __future__ import annotations

import re


RULES = (
    ("spam", r"\bremoved from\b"),
    ("spam", r"\bviagra\b"),
    ("ham", r"(?im)^in-reply-to\s*:"),
    ("ham", r"(?im)^references\s*:"),
)


def classify(text, labels):
    """Return a guarded label match or abstain for the frozen model fallback."""
    if not isinstance(text, str) or len(text) > 500_000:
        return None
    allowed = set(labels)
    for label, pattern in RULES:
        if label in allowed and re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE):
            return {"label": label, "matched_rule": pattern}
    return None
'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"output exists: {args.output}")
    shutil.copytree(args.baseline, args.output)
    sop_path = args.output / "skills/spamassassin-classification/SKILL.md"
    sop = sop_path.read_text(encoding="utf-8")
    original = "Classify the evidence into exactly one known bucket: `ham`, `spam`."
    replacement = (
        "Run the bounded local `classify.py` rules; accept only a supplied label with a named matching rule. "
        "Abstain on every unmatched email so the exact English fallback handles it. "
        "<!-- pland:command fallback=S03 -->\n"
        f"   Fallback [S03]: {original} <!-- pland:fallback -->"
    )
    marked = f"{original} <!-- pland:english -->"
    if marked not in sop:
        raise SystemExit("frozen S03 instruction not found")
    sop_path.write_text(sop.replace(marked, replacement), encoding="utf-8")
    (args.output / "classify.py").write_text(CLASSIFIER, encoding="utf-8")
    construction = {
        "schema_version": 1,
        "candidate_id": "candidate-01",
        "development_only": True,
        "hypothesis": "High-precision opt-out and product cues can identify some spam locally, while reply-thread headers can identify some ham and every unmatched email abstains.",
        "dependencies": ["Python standard library"],
        "network": "none",
        "side_effects": "none",
        "cache": {"used": False, "reason": "Each email is evaluated once; lookup reuse is absent."},
        "parallelism": {"used": False, "reason": "One bounded regex pass is cheaper than internal coordination; run-level concurrency remains eight."},
        "input_contract": "One sanitized raw email string up to 500,000 characters and the supplied label list.",
        "output_contract": "A supplied label plus matched_rule, or None to trigger the exact English fallback.",
    }
    (args.output / "construction.json").write_text(json.dumps(construction, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"candidate": "candidate-01", "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
