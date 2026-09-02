#!/usr/bin/env python3
"""Create check-in-safe proof for legacy text-document benchmark subsets."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def portable_path(value: object) -> object:
    if not isinstance(value, str):
        return value
    path = Path(value)
    if not path.is_absolute():
        return value
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.name


def input_manifest(root: Path, rows: list[dict[str, str]]) -> tuple[str, dict[str, str]]:
    bindings = []
    hashes = {}
    for row in rows:
        path = root / row["input"]
        if not path.is_file():
            continue
        value = digest(path)
        hashes[row["id"]] = value
        bindings.append((row["id"], row["split"], row["input"], value))
    return hashlib.sha256(json.dumps(sorted(bindings)).encode()).hexdigest(), hashes


def pilot_content_hashes(root: Path | None) -> set[str]:
    if root is None or not (root / "evals.csv").is_file():
        return set()
    with (root / "evals.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return {digest(root / row["input"]) for row in rows if (root / row["input"]).is_file()}


def audit(root: Path, repeat: Path | None = None, pilot: Path | None = None) -> dict:
    with (root / "evals.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    selection = json.loads((root / "selection.json").read_text(encoding="utf-8"))
    summary_path = root / "dataset-summary.json"
    ids = [row["id"] for row in rows]
    split_ids: dict[str, set[str]] = defaultdict(set)
    contents: dict[str, list[str]] = defaultdict(list)
    missing, path_leaks, source_hash_errors = [], [], []
    for row in rows:
        split_ids[row["split"]].add(row["id"])
        path = root / row["input"]
        if not path.exists():
            missing.append(row["input"])
            continue
        contents[digest(path)].append(row["id"])
        if row["output"].casefold().replace(" ", "-") in row["input"].casefold():
            path_leaks.append(row["id"])
    records = selection.get("records", selection.get("selected", []))
    manifest_pairs = {(str(item["id"]), item["experiment_split"] if "experiment_split" in item else item["split"])
                      for item in records}
    eval_pairs = {(row["id"], row["split"]) for row in rows}
    prior_pilot_ids = set(map(str, selection.get("prior_pilot_ids", [])))
    pilot_overlap = sorted(set(ids) & prior_pilot_ids)
    expected_source = {"development": "train", "validation": "validation", "test": "test"}
    source_split_errors = [item["id"] for item in records if "source_split" in item
                           and item["source_split"] != expected_source[item["experiment_split"]]]
    runtime_manifest, runtime_hashes = input_manifest(root, rows)
    source_binding_errors = []
    for item in records:
        source = Path(item["source"]) if item.get("source") else root / item.get("ocr_path", "")
        expected = item.get("source_sha256") or item.get("ocr_sha256")
        if expected and (not source.is_file() or digest(source) != expected):
            source_hash_errors.append(item["id"])
        runtime_expected = runtime_hashes.get(str(item["id"]))
        if expected and runtime_expected != expected:
            source_binding_errors.append(item["id"])
    prior_hashes = pilot_content_hashes(pilot)
    pilot_content_overlap = sorted(
        row["id"] for row in rows
        if runtime_hashes.get(row["id"]) in prior_hashes
    )
    overlaps = {
        f"{left}:{right}": len(split_ids[left] & split_ids[right])
        for index, left in enumerate(sorted(split_ids)) for right in sorted(split_ids)[index + 1:]
    }
    by_split_class = {
        split: dict(sorted(Counter(row["output"] for row in rows if row["split"] == split).items()))
        for split in sorted(split_ids)
    }
    repeatability = None
    if repeat:
        repeat_manifest, _ = input_manifest(repeat, rows)
        repeatability = {
            name: digest(root / name) == digest(repeat / name)
            for name in ("evals.csv", "selection.json", "dataset-summary.json") if (root / name).exists()
        }
        repeatability["input_manifest"] = runtime_manifest == repeat_manifest
    checks = {
        "unique_ids": len(ids) == len(set(ids)),
        "split_overlap_count": sum(overlaps.values()),
        "duplicate_content_groups": sum(len(owners) > 1 for owners in contents.values()),
        "missing_inputs": len(missing),
        "label_in_runtime_path": len(path_leaks),
        "source_hash_errors": len(source_hash_errors),
        "selection_source_bindings_match_inputs": not source_binding_errors,
        "selection_manifest_matches_evals": manifest_pairs == eval_pairs,
        "pilot_overlap_count": len(pilot_overlap),
        "pilot_content_overlap_count": len(pilot_content_overlap),
        "source_split_integrity": not source_split_errors,
        "repeatability": repeatability,
    }
    passed = (checks["unique_ids"] and checks["split_overlap_count"] == 0
              and checks["duplicate_content_groups"] == 0 and checks["missing_inputs"] == 0
              and checks["label_in_runtime_path"] == 0 and checks["source_hash_errors"] == 0
              and checks["selection_source_bindings_match_inputs"]
              and checks["selection_manifest_matches_evals"]
              and not pilot_overlap and not pilot_content_overlap and not source_split_errors
              and (repeatability is None or all(repeatability.values())))
    return {
        "schema_version": 1,
        "dataset": selection.get("dataset", "QS-OCR-Small/Tobacco3482"),
        "counts": {"total": len(rows), "by_split": dict(Counter(row["split"] for row in rows)),
                   "by_split_and_class": by_split_class},
        "checks": checks,
        "passed": passed,
        "hashes": {"evals_sha256": digest(root / "evals.csv"),
                   "selection_sha256": digest(root / "selection.json"),
                   "summary_sha256": digest(summary_path) if summary_path.exists() else None,
                   "input_manifest_sha256": runtime_manifest},
        "source": {key: portable_path(selection.get(key)) for key in ("corpus", "audit", "audit_sha256", "source_release_sha256", "revision") if key in selection},
        "capacity": {key: selection.get(key) for key in ("requested_counts", "available_source_counts", "actual_counts", "capacity_shortfall") if key in selection},
        "exclusions": (json.loads(summary_path.read_text()).get("counts", {}) if summary_path.exists()
                       else dict(Counter(item["reason"] for item in selection.get("exclusions", [])))),
        "failures": {"overlaps": overlaps, "missing": missing, "path_leaks": path_leaks,
                     "source_hash_errors": source_hash_errors,
                     "source_binding_errors": source_binding_errors,
                     "pilot_overlap_ids": pilot_overlap,
                     "pilot_content_overlap_ids": pilot_content_overlap,
                     "source_split_errors": source_split_errors,
                     "duplicate_groups": {key: owners for key, owners in contents.items() if len(owners) > 1}},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--repeat", type=Path)
    parser.add_argument("--pilot-dataset", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    proof = audit(args.dataset, args.repeat, args.pilot_dataset)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": proof["passed"], **proof["counts"]}, sort_keys=True))
    return 0 if proof["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
