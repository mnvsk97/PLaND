#!/usr/bin/env python3
"""Summarize label-predictive phrases from the development split only."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"output exists: {args.output}")
    with (args.dataset / "evals.csv").open(newline="", encoding="utf-8") as handle:
        rows = [row for row in csv.DictReader(handle) if row["split"] == "development"]
    phrases: dict[str, Counter[str]] = defaultdict(Counter)
    label_counts: Counter[str] = Counter()
    for row in rows:
        label = json.loads(row["output"])["label"]
        label_counts[label] += 1
        payload = json.loads((args.dataset / row["input"]).read_text(encoding="utf-8"))
        text = payload.get("text") or payload.get("narrative") or payload.get("raw_email")
        tokens = re.findall(r"[a-z0-9]+", text.casefold())
        seen = set()
        for size in (1, 2, 3, 4):
            seen.update(" ".join(tokens[index:index + size]) for index in range(len(tokens) - size + 1))
        for phrase in seen:
            phrases[phrase][label] += 1
    candidates = []
    for phrase, counts in phrases.items():
        total = sum(counts.values())
        label, support = counts.most_common(1)[0]
        precision = support / total
        if support >= 3 and precision >= 0.95:
            candidates.append({"phrase": phrase, "label": label, "support": support,
                               "total": total, "precision": precision})
    candidates.sort(key=lambda item: (-item["support"], -len(item["phrase"].split()), item["phrase"]))
    result = {"schema_version": 1, "split": "development", "cases": len(rows),
              "label_counts": dict(sorted(label_counts.items())), "candidates": candidates[:500]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"cases": len(rows), "candidate_phrases": len(candidates)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
