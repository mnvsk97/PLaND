#!/usr/bin/env python3
"""Build a conservative CFPB product-routing command candidate."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


CLASSIFIER = r'''"""Conservative, standard-library CFPB product classifier."""
from __future__ import annotations

import re


RULES = (
    ("Prepaid card", r"\bprepaid (?:debit |gift )?card\b|\b(?:vanilla|incomm)\b.{0,80}\b(?:visa|card)\b|\bvisa gift card\b"),
    ("Student loan", r"\bstudent loans?\b|\b(?:mohela|navient|nelnet)\b|\bdepartment of education\b.{0,100}\bloans?\b"),
    ("Mortgage", r"\bmortgage\b|\bforeclosure\b|\bhome equity line of credit\b|\bheloc\b|\bescrow account\b"),
    ("Money transfer, virtual currency, or money service", r"\b(?:zelle|venmo|coinbase|cryptocurrency|western union)\b|\bcash app\b|\bwire transfer\b"),
    ("Payday loan, title loan, personal loan, or advance loan", r"\b(?:payday|title|personal|advance) loans?\b|\baffirm\b"),
    ("Vehicle loan or lease", r"\b(?:auto|vehicle|car) loans?\b|\bauto lease\b|\bvehicle lease\b|\bbridgecrest\b"),
    ("Checking or savings account", r"\bchecking account\b|\bsavings account\b|\bdeposit account\b"),
    ("Debt collection", r"\bdebt collector\b|\bcollection agency\b|\bcollect(?:ing|ion of) (?:a |the )?debt\b"),
    ("Credit reporting or other personal consumer reports", r"\b(?:equifax|experian|transunion)\b|\bconsumer reports?\b|\bcredit report(?:ing)?\b"),
    ("Credit card", r"\bcredit card account\b|\bmy credit card\b|\bcard issuer\b"),
)


def classify(text, labels):
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
    sop_path = args.output / "skills/cfpb-classification/SKILL.md"
    sop = sop_path.read_text(encoding="utf-8")
    original = "Classify the evidence into exactly one known bucket: `Checking or savings account`, `Credit card`, `Credit reporting or other personal consumer reports`, `Debt collection`, `Money transfer, virtual currency, or money service`, `Mortgage`, `Payday loan, title loan, personal loan, or advance loan`, `Prepaid card`, `Student loan`, `Vehicle loan or lease`."
    replacement = (
        "Run the bounded local `classify.py` product rules; accept only a supplied label with a named matching rule. "
        "Abstain on every ambiguous complaint so the exact English fallback handles it. "
        "<!-- pland:command fallback=S03 -->\n"
        f"   Fallback [S03]: {original} <!-- pland:fallback -->"
    )
    marked = f"{original} <!-- pland:english -->"
    if marked not in sop:
        raise SystemExit("frozen S03 instruction not found")
    sop_path.write_text(sop.replace(marked, replacement), encoding="utf-8")
    (args.output / "classify.py").write_text(CLASSIFIER, encoding="utf-8")
    construction = {"schema_version": 1, "candidate_id": "candidate-01",
                    "development_only": True,
                    "hypothesis": "Explicit financial-product phrases can route common CFPB complaints locally while ambiguous cross-product narratives abstain.",
                    "dependencies": ["Python standard library"], "network": "none", "side_effects": "none",
                    "cache": {"used": False, "reason": "Each narrative is evaluated once."},
                    "parallelism": {"used": False, "reason": "One bounded regex pass is cheaper; run-level concurrency remains eight."}}
    (args.output / "construction.json").write_text(json.dumps(construction, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"candidate": "candidate-01", "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
