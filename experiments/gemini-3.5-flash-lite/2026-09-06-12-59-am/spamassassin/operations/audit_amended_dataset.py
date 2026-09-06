#!/usr/bin/env python3
"""Audit the one-for-one SpamAssassin selection amendment."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


def rows(root: Path) -> list[dict[str, str]]:
    with (root / "evals.csv").open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def normalized(root: Path, row: dict[str, str]) -> str:
    payload = json.loads((root / row["input"]).read_text(encoding="utf-8"))
    return hashlib.sha256(" ".join(payload["raw_email"].split()).casefold().encode()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True, type=Path)
    parser.add_argument("--amended", required=True, type=Path)
    parser.add_argument("--prior-opened", required=True, type=Path)
    parser.add_argument("--blocked-case-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"output exists: {args.output}")
    base = rows(args.base)
    amended = rows(args.amended)
    prior = rows(args.prior_opened)
    base_by_id = {row["id"]: row for row in base}
    amended_by_id = {row["id"]: row for row in amended}
    removed = sorted(set(base_by_id) - set(amended_by_id))
    added = sorted(set(amended_by_id) - set(base_by_id))
    replacement = amended_by_id[added[0]] if len(added) == 1 else None
    blocked = base_by_id.get(args.blocked_case_id)
    stable_ids = set(base_by_id) & set(amended_by_id)
    base_content = {normalized(args.base, row) for row in base}
    prior_ids = {row["id"] for row in prior}
    prior_content = {normalized(args.prior_opened, row) for row in prior}
    replacement_content = normalized(args.amended, replacement) if replacement else None
    amended_split = Counter(row["split"] for row in amended)
    amended_labels = Counter(json.loads(row["output"])["label"] for row in amended
                             if row["split"] == "validation")
    checks = {
        "total_count_unchanged": len(base) == len(amended) == 2000,
        "exactly_one_removed": removed == [args.blocked_case_id],
        "exactly_one_added": len(added) == 1,
        "blocked_was_selection": blocked is not None and blocked["split"] == "validation",
        "replacement_is_selection": replacement is not None and replacement["split"] == "validation",
        "same_reference_label": replacement is not None and blocked is not None
            and replacement["output"] == blocked["output"],
        "all_other_rows_identical": all(base_by_id[item] == amended_by_id[item] for item in stable_ids),
        "split_counts_preserved": amended_split == {"development": 500, "validation": 1000, "test": 500},
        "selection_balance_preserved": amended_labels == {"ham": 500, "spam": 500},
        "replacement_id_previously_unopened": replacement is not None
            and replacement["id"] not in prior_ids,
        "replacement_content_previously_unopened": replacement_content not in prior_content,
        "replacement_id_unique_from_base": replacement is not None and replacement["id"] not in base_by_id,
        "replacement_content_unique_from_base": replacement_content not in base_content,
        "amendment_receipt_present": (args.amended / "amendment-receipt.json").is_file(),
    }
    result = {
        "schema_version": 1,
        "blocked_case_id": args.blocked_case_id,
        "replacement_case_id": added[0] if len(added) == 1 else None,
        "replacement_label": json.loads(replacement["output"])["label"] if replacement else None,
        "counts": {"total": len(amended), "splits": dict(amended_split),
                   "selection_labels": dict(amended_labels)},
        "checks": checks,
        "passed": all(checks.values()),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
