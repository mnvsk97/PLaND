#!/usr/bin/env python3
"""Build a one-for-one SpamAssassin selection amendment from a reserve pool."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized_hash(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    text = payload.get("raw_email")
    normalized = " ".join(str(text).split()).casefold()
    return hashlib.sha256(normalized.encode()).hexdigest()


def read_rows(root: Path) -> list[dict[str, str]]:
    with (root / "evals.csv").open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dataset", required=True, type=Path)
    parser.add_argument("--reserve-dataset", required=True, type=Path)
    parser.add_argument("--blocked-case-id", action="append", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"output exists: {args.output}")
    base_rows = read_rows(args.base_dataset)
    reserve_rows = read_rows(args.reserve_dataset)
    blocked = set(args.blocked_case_id)
    blocked_rows = [row for row in base_rows if row["id"] in blocked]
    if len(blocked_rows) != len(blocked) or any(row["split"] != "validation" for row in blocked_rows):
        raise SystemExit("each blocked case must occur exactly once in base validation")
    used_ids = {row["id"] for row in base_rows}
    used_content = {normalized_hash(args.base_dataset / row["input"]) for row in base_rows}
    replacements = []
    reserved_ids = set()
    for old in blocked_rows:
        candidate = next((row for row in reserve_rows
                          if row["split"] == "validation"
                          and row["output"] == old["output"]
                          and row["id"] not in used_ids
                          and row["id"] not in reserved_ids
                          and normalized_hash(args.reserve_dataset / row["input"]) not in used_content), None)
        if candidate is None:
            raise SystemExit(f"no unopened same-label replacement for {old['id']}")
        replacement = dict(candidate)
        replacement["split"] = "validation"
        replacements.append((old, replacement))
        reserved_ids.add(replacement["id"])
        used_content.add(normalized_hash(args.reserve_dataset / replacement["input"]))
    shutil.copytree(args.base_dataset, args.output)
    replacement_by_old = {old["id"]: new for old, new in replacements}
    amended_rows = [replacement_by_old.get(row["id"], row) for row in base_rows]
    for _, replacement in replacements:
        source = args.reserve_dataset / replacement["input"]
        destination = args.output / replacement["input"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    fieldnames = list(base_rows[0])
    with (args.output / "evals.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(amended_rows)
    selection_path = args.output / "selection.json"
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    for item in selection["selected"]:
        replacement = replacement_by_old.get(item["id"])
        if replacement:
            item["id"] = replacement["id"]
    selection["amendment"] = {
        "number": 1,
        "policy": "one-for-one same-label replacement after terminal PROHIBITED_CONTENT",
        "base_evals_sha256": sha(args.base_dataset / "evals.csv"),
        "base_selection_sha256": sha(args.base_dataset / "selection.json"),
        "replacements": [{"blocked_id": old["id"], "replacement_id": new["id"],
                          "label": json.loads(old["output"])["label"]}
                         for old, new in replacements],
    }
    selection_path.write_text(json.dumps(selection, indent=2) + "\n", encoding="utf-8")
    summary = {
        "cases": len(amended_rows),
        "by_split": dict(Counter(row["split"] for row in amended_rows)),
        "by_output": dict(Counter(row["output"] for row in amended_rows)),
    }
    (args.output / "dataset-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    receipt = {
        "schema_version": 1,
        "base_dataset": str(args.base_dataset.resolve()),
        "reserve_dataset": str(args.reserve_dataset.resolve()),
        "base_evals_sha256": sha(args.base_dataset / "evals.csv"),
        "base_selection_sha256": sha(args.base_dataset / "selection.json"),
        "amended_evals_sha256": sha(args.output / "evals.csv"),
        "amended_selection_sha256": sha(args.output / "selection.json"),
        "split_counts": summary["by_split"],
        "label_counts": summary["by_output"],
        "replacements": selection["amendment"]["replacements"],
        "case_count_unchanged": len(amended_rows) == len(base_rows) == 2000,
        "selection_count_unchanged": summary["by_split"].get("validation") == 1000,
        "selection_balance_preserved": Counter(
            json.loads(row["output"])["label"] for row in amended_rows if row["split"] == "validation"
        ) == {"ham": 500, "spam": 500},
    }
    (args.output / "amendment-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt))
    return 0 if all((receipt["case_count_unchanged"], receipt["selection_count_unchanged"],
                     receipt["selection_balance_preserved"])) else 1


if __name__ == "__main__":
    raise SystemExit(main())
