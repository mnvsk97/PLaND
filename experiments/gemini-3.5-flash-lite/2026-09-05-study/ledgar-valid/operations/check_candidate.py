#!/usr/bin/env python3
"""Measure command coverage and precision on development cases only."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
from collections import Counter
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--classifier", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"output exists: {args.output}")
    spec = importlib.util.spec_from_file_location("candidate_classifier", args.classifier)
    if spec is None or spec.loader is None:
        raise SystemExit("cannot import classifier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with (args.dataset / "evals.csv").open(newline="", encoding="utf-8") as handle:
        all_rows = list(csv.DictReader(handle))
    rows = [row for row in all_rows if row["split"] == "development"]
    labels = sorted({json.loads(row["output"])["label"] for row in all_rows})
    resolved = correct = 0
    by_rule: Counter[tuple[str, str, bool]] = Counter()
    for row in rows:
        expected = json.loads(row["output"])["label"]
        payload = json.loads((args.dataset / row["input"]).read_text(encoding="utf-8"))
        text = payload.get("text") or payload.get("narrative") or payload.get("raw_email")
        result = module.classify(text, labels)
        if result is None:
            continue
        if result.get("label") not in labels or not result.get("matched_rule"):
            raise SystemExit("classifier returned an invalid guarded result")
        resolved += 1
        is_correct = result["label"] == expected
        correct += is_correct
        by_rule[(result["label"], result["matched_rule"], is_correct)] += 1
    output = {
        "schema_version": 1,
        "split": "development",
        "cases": len(rows),
        "resolved": resolved,
        "coverage": resolved / len(rows),
        "correct": correct,
        "precision": correct / resolved if resolved else None,
        "abstained": len(rows) - resolved,
        "rule_outcomes": [
            {"label": label, "rule": rule, "correct": outcome, "cases": count}
            for (label, rule, outcome), count in sorted(by_rule.items())
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: output[key] for key in ("cases", "resolved", "coverage", "correct", "precision", "abstained")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
