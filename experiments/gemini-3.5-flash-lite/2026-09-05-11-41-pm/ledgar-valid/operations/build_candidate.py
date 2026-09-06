#!/usr/bin/env python3
"""Build one conservative LEDGAR command candidate from development evidence."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


CLASSIFIER = r'''"""Conservative, standard-library LEDGAR clause classifier."""
from __future__ import annotations

import re


RULES = (
    ("Counterparts", r"\bcounterparts?\b"),
    ("Governing Laws", r"(?:\bgoverned by\b|\bconstrued in accordance with\b).{0,140}\blaws?\b|\blaws?\b.{0,100}\bstate of\b"),
    ("Severability", r"\b(?:invalid|illegal|unenforceable|invalidity)\b.{0,180}\b(?:provision|remainder|remaining)\b|\bprovision\b.{0,180}\b(?:invalid|illegal|unenforceable)\b"),
    ("Entire Agreements", r"\bentire agreement\b|\bsupersed(?:e|es|ed|ing)\b.{0,100}\bprior\b|\ball prior\b.{0,100}\bagreements?\b|\bagreements and understandings\b"),
    ("Notices", r"\bnotices?\b"),
    ("Expenses", r"\bexpenses incurred\b|\bcosts and expenses\b|\breimburse\b.{0,100}\bexpenses\b"),
    ("Assignments", r"\bassign\b|\bassignee\b|\ban assignment\b|\bbe assigned\b"),
    ("Amendments", r"\b(?:any|no|such|the) amendment\b"),
    ("Survival", r"\bsurviv(?:e|es|ed|al)\b|\brepayment satisfaction or discharge\b"),
    ("Terms", r"\bshall commence\b|\bthe term shall\b|\bdate and shall continue\b"),
)


def classify(text, labels):
    """Return a guarded label match or abstain for the frozen model fallback."""
    if not isinstance(text, str) or len(text) > 200_000:
        return None
    allowed = set(labels)
    normalized = " ".join(text.casefold().split())
    for label, pattern in RULES:
        if label in allowed and re.search(pattern, normalized, flags=re.DOTALL):
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
    sop_path = args.output / "skills/ledgar-classification/SKILL.md"
    sop = sop_path.read_text(encoding="utf-8")
    original = "Classify the evidence into exactly one known bucket: `Amendments`, `Assignments`, `Counterparts`, `Entire Agreements`, `Expenses`, `Governing Laws`, `Notices`, `Severability`, `Survival`, `Terms`."
    replacement = (
        "Run the bounded local `classify.py` rules; accept only a supplied label with a named matching rule. "
        "Abstain on every unrecognized clause so the exact English fallback handles it. "
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
        "hypothesis": "High-precision legal boilerplate phrases can resolve common LEDGAR clauses locally while ambiguous clauses abstain to the frozen S03 fallback.",
        "dependencies": ["Python standard library"],
        "network": "none",
        "side_effects": "none",
        "cache": {"used": False, "reason": "Each clause is evaluated once; lookup reuse is absent."},
        "parallelism": {"used": False, "reason": "One bounded regex pass is cheaper than coordinating internal workers; run-level concurrency remains eight."},
        "input_contract": "One nonempty clause string up to 200,000 characters and the supplied label list.",
        "output_contract": "A supplied label plus matched_rule, or None to trigger the exact English fallback.",
    }
    (args.output / "construction.json").write_text(json.dumps(construction, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"candidate": "candidate-01", "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
