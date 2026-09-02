#!/usr/bin/env python3
"""Audit a prepared dataset and emit check-in-safe reproducibility evidence."""
from __future__ import annotations

import argparse, csv, hashlib, json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""): value.update(chunk)
    return value.hexdigest()

def normalized_content(payload: dict[str, Any]) -> str:
    for key in ("text", "narrative", "raw_email"):
        if key in payload: return " ".join(str(payload[key]).split()).casefold()
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def audit(root: Path, source_dir: Path | None = None,
          pilot_datasets: list[Path] | None = None) -> dict[str, Any]:
    with (root / "evals.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    selection = json.loads((root / "selection.json").read_text())
    source_dir = source_dir or root / "sources"
    source_results = []
    for item in selection.get("sources", []):
        path = source_dir / item["path"]
        source_results.append({"path": item["path"], "exists": path.is_file(),
                               "sha256_match": path.is_file() and digest(path) == item["sha256"]})
    ids_by_split: dict[str, set[str]] = defaultdict(set)
    label_counts: Counter[tuple[str, str]] = Counter()
    content_owners: dict[str, list[str]] = defaultdict(list)
    leakage = []
    missing = []
    case_hashes = []
    current_content_hashes = set()
    for row in rows:
        ids_by_split[row["split"]].add(row["id"])
        expected = json.loads(row["output"])
        label_counts[(row["split"], expected["label"])] += 1
        path = root / row["input"]
        if not path.is_file(): missing.append(row["input"]); continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if "label" in payload or "output" in payload or row["output"] in path.read_text(encoding="utf-8"):
            leakage.append(row["id"])
        content_hash = hashlib.sha256(normalized_content(payload).encode()).hexdigest()
        current_content_hashes.add(content_hash)
        content_owners[content_hash].append(row["id"])
        case_hashes.append((row["input"], digest(path)))
    overlaps = {}
    splits = sorted(ids_by_split)
    for index, left in enumerate(splits):
        for right in splits[index + 1:]: overlaps[f"{left}:{right}"] = sorted(ids_by_split[left] & ids_by_split[right])
    duplicates = {key: value for key, value in content_owners.items() if len(value) > 1}
    labels = sorted({label for _, label in label_counts})
    by_split_label = {split: {label: label_counts[(split, label)] for label in labels} for split in splits}
    balance = {split: len(set(counts.values())) == 1 for split, counts in by_split_label.items()}
    source_mapping = selection.get("source_split_mapping")
    source_split_violations = []
    if source_mapping:
        for row in rows:
            upstream = json.loads(row["metadata"]).get("upstream_split")
            if upstream != source_mapping.get(row["split"]):
                source_split_violations.append(row["id"])
    pilot_ids, pilot_contents, pilot_manifest = set(), set(), []
    for pilot in pilot_datasets or []:
        with (pilot / "evals.csv").open(newline="", encoding="utf-8") as handle:
            pilot_rows = list(csv.DictReader(handle))
        pilot_case_hashes = []
        for row in pilot_rows:
            path = pilot / row["input"]
            payload = json.loads(path.read_text(encoding="utf-8"))
            pilot_ids.add(row["id"])
            pilot_contents.add(hashlib.sha256(normalized_content(payload).encode()).hexdigest())
            pilot_case_hashes.append((row["input"], digest(path)))
        pilot_manifest.append({"path": str(pilot), "evals_sha256": digest(pilot / "evals.csv"),
                               "cases": len(pilot_rows), "case_manifest_sha256": hashlib.sha256(
                                   json.dumps(sorted(pilot_case_hashes), sort_keys=True,
                                              separators=(",", ":")).encode()).hexdigest()})
    current_ids = {row["id"] for row in rows}
    pilot_overlap_count = len(current_ids & pilot_ids) + len(current_content_hashes & pilot_contents)
    selected = selection.get("selected", [])
    selected_pairs = {(item["id"], item["split"]) for item in selected}
    row_pairs = {(row["id"], row["split"]) for row in rows}
    proof = {
        "schema_version": 1, "dataset": selection.get("dataset"),
        "counts": {"total": len(rows), "by_split": dict(Counter(row["split"] for row in rows)),
                   "by_split_and_label": by_split_label},
        "checks": {
            "unique_ids": len({row["id"] for row in rows}) == len(rows),
            "split_id_overlap_count": sum(len(value) for value in overlaps.values()),
            "content_duplicate_count": len(duplicates), "runtime_label_leakage_count": len(leakage),
            "missing_case_count": len(missing), "balanced_within_each_split": balance,
            "selection_manifest_matches_evals": selected_pairs == row_pairs,
            "source_hashes_match": all(item["sha256_match"] for item in source_results),
            "source_split_integrity": not source_split_violations,
            "pilot_overlap_count": pilot_overlap_count,
            "exclusion_manifest_matches_pilot": selection.get("excluded_datasets", []) == pilot_manifest,
        },
        "hashes": {"evals_sha256": digest(root / "evals.csv"),
                   "selection_sha256": digest(root / "selection.json"),
                   "case_manifest_sha256": hashlib.sha256(json.dumps(sorted(case_hashes)).encode()).hexdigest()},
        "sources": selection.get("sources", []),
        "source_verification": source_results,
        "eligible_unique_by_label": {
            label: selection.get("eligible_unique_by_label", {}).get(label)
            for label in selection.get("labels", labels)
        },
        "requested_split_counts": selection.get("requested_split_counts", {}),
        "source_split_mapping": source_mapping,
        "eligible_unique_by_label_and_source_split": selection.get("eligible_unique_by_label_and_source_split"),
        "exclusion_manifest": selection.get("excluded_datasets", []),
        "failures": {"overlaps": overlaps, "duplicates": duplicates, "leakage_ids": leakage, "missing": missing},
    }
    checks = proof["checks"]
    proof["passed"] = (checks["unique_ids"] and checks["split_id_overlap_count"] == 0
                       and checks["content_duplicate_count"] == 0
                       and checks["runtime_label_leakage_count"] == 0
                       and checks["missing_case_count"] == 0
                       and all(checks["balanced_within_each_split"].values())
                       and checks["selection_manifest_matches_evals"]
                       and checks["source_hashes_match"]
                       and checks["source_split_integrity"]
                       and checks["pilot_overlap_count"] == 0
                       and checks["exclusion_manifest_matches_pilot"])
    return proof

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--repeat-dataset", type=Path,
                        help="Independently prepared copy used to prove byte repeatability")
    parser.add_argument("--source-dir", type=Path,
                        help="Directory containing the frozen raw source files")
    parser.add_argument("--pilot-dataset", action="append", default=[], type=Path,
                        help="Prior prepared dataset that must have zero overlap")
    args = parser.parse_args()
    proof = audit(args.dataset, args.source_dir, args.pilot_dataset)
    if args.repeat_dataset:
        repeat = audit(args.repeat_dataset, args.source_dir, args.pilot_dataset)
        proof["repeatability"] = {
            "evals_sha256_match": proof["hashes"]["evals_sha256"] == repeat["hashes"]["evals_sha256"],
            "selection_sha256_match": proof["hashes"]["selection_sha256"] == repeat["hashes"]["selection_sha256"],
            "case_manifest_sha256_match": proof["hashes"]["case_manifest_sha256"] == repeat["hashes"]["case_manifest_sha256"],
        }
        proof["passed"] = proof["passed"] and all(proof["repeatability"].values())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps({"passed": proof["passed"], **proof["counts"]}, sort_keys=True))
    return 0 if proof["passed"] else 1

if __name__ == "__main__": raise SystemExit(main())
