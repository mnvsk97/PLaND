#!/usr/bin/env python3
"""Create check-in-safe integrity and repeatability proof for prepared SROIE."""

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


def manifests(root: Path, rows: list[dict[str, str]]) -> tuple[str, str]:
    cases, images = [], []
    for row in rows:
        case_path = root / row["input"]
        case = json.loads(case_path.read_text(encoding="utf-8"))
        image_path = root / case["image"]
        cases.append((row["id"], digest(case_path)))
        images.append((row["id"], digest(image_path)))
    return (hashlib.sha256(json.dumps(sorted(cases)).encode()).hexdigest(),
            hashlib.sha256(json.dumps(sorted(images)).encode()).hexdigest())


def image_hashes_for_dataset(root: Path | None) -> set[str]:
    if root is None or not (root / "evals.csv").is_file():
        return set()
    with (root / "evals.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    values = set()
    for row in rows:
        case_path = root / row["input"]
        if not case_path.is_file():
            continue
        case = json.loads(case_path.read_text(encoding="utf-8"))
        image_path = root / case["image"]
        if image_path.is_file():
            values.add(digest(image_path))
    return values


def audit(root: Path, repeat: Path | None = None, pilot: Path | None = None,
          source_snapshot: Path | None = None) -> dict:
    with (root / "evals.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    selection = json.loads((root / "selection.json").read_text(encoding="utf-8"))
    ids = [row["id"] for row in rows]
    prior_pilot_ids = set(map(str, selection.get("prior_pilot_ids", [])))
    pilot_overlap = sorted(set(ids) & prior_pilot_ids)
    split_ids: dict[str, set[str]] = defaultdict(set)
    missing, hash_errors, leakage, boundary_errors = [], [], [], []
    image_hashes: dict[str, list[str]] = defaultdict(list)
    ocr_hashes: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        split_ids[row["split"]].add(row["id"])
        case_path = root / row["input"]
        if not case_path.exists():
            missing.append(row["input"]); continue
        case_text = case_path.read_text(encoding="utf-8")
        case = json.loads(case_text)
        expected = json.loads(row["output"])
        if row["output"] in case_text or any(key in case for key in ("output", "expected")):
            leakage.append(row["id"])
        image_path = root / case["image"]
        if not image_path.exists():
            missing.append(case["image"]); continue
        actual_hash = digest(image_path)
        metadata = json.loads(row["metadata"])
        if actual_hash != metadata["image_sha256"]:
            hash_errors.append(row["id"])
        image_hashes[actual_hash].append(row["id"])
        ocr_hash = hashlib.sha256(json.dumps(case["frozen_ocr"], sort_keys=True).encode()).hexdigest()
        ocr_hashes[ocr_hash].append(row["id"])
        official = metadata["source_split"]
        if (row["split"] in {"development", "validation"} and official != "train") or (row["split"] == "test" and official != "test"):
            boundary_errors.append(row["id"])
        if set(expected) != {"company", "date", "address", "total"}:
            leakage.append(row["id"])
    overlaps = sum(len(split_ids[left] & split_ids[right]) for index, left in enumerate(sorted(split_ids))
                   for right in sorted(split_ids)[index + 1:])
    selected_pairs = {(str(item["id"]), item["split"]) for item in selection.get("selected", [])}
    eval_pairs = {(row["id"], row["split"]) for row in rows}
    pilot_images = image_hashes_for_dataset(pilot)
    pilot_content_overlap = sorted(
        identifier for value, identifiers in image_hashes.items() if value in pilot_images
        for identifier in identifiers
    )
    case_manifest, image_manifest = manifests(root, rows)
    declared_source = selection.get("sources", [{}])[0]
    if source_snapshot is None and declared_source.get("path"):
        candidates = [root / "sources" / declared_source["path"], root / declared_source["path"]]
        source_snapshot = next((path for path in candidates if path.is_file()), None)
    source_snapshot_verified = bool(
        source_snapshot and source_snapshot.is_file()
        and digest(source_snapshot) == declared_source.get("sha256")
        and source_snapshot.stat().st_size == declared_source.get("bytes")
    )
    repeatability = None
    if repeat:
        with (repeat / "evals.csv").open(encoding="utf-8", newline="") as handle:
            repeat_rows = list(csv.DictReader(handle))
        repeat_case_manifest, repeat_image_manifest = manifests(repeat, repeat_rows)
        repeatability = {
            "evals": digest(root / "evals.csv") == digest(repeat / "evals.csv"),
            "selection": digest(root / "selection.json") == digest(repeat / "selection.json"),
            "summary": digest(root / "dataset-summary.json") == digest(repeat / "dataset-summary.json"),
            "cases": case_manifest == repeat_case_manifest,
            "images": image_manifest == repeat_image_manifest,
        }
    checks = {
        "unique_ids": len(ids) == len(set(ids)), "split_overlap_count": overlaps,
        "missing_files": len(missing), "image_hash_errors": len(hash_errors),
        "runtime_expected_output_leakage": len(set(leakage)),
        "official_boundary_errors": len(boundary_errors),
        "source_split_integrity": not boundary_errors,
        "pilot_overlap_count": len(pilot_overlap),
        "pilot_image_overlap_count": len(pilot_content_overlap),
        "selection_manifest_matches_evals": selected_pairs == eval_pairs,
        "source_snapshot_verified": source_snapshot_verified,
        "duplicate_image_groups": sum(len(value) > 1 for value in image_hashes.values()),
        "duplicate_frozen_ocr_groups": sum(len(value) > 1 for value in ocr_hashes.values()),
        "repeatability": repeatability,
    }
    passed = (checks["unique_ids"] and not overlaps and not missing and not hash_errors and not leakage
              and not boundary_errors and checks["duplicate_image_groups"] == 0
              and not pilot_overlap and not pilot_content_overlap
              and checks["selection_manifest_matches_evals"] and source_snapshot_verified
              and checks["duplicate_frozen_ocr_groups"] == 0
              and (repeatability is None or all(repeatability.values())))
    return {
        "schema_version": 1, "dataset": selection["dataset"],
        "counts": {"total": len(rows), "by_split": dict(Counter(row["split"] for row in rows)),
                   "official_source": selection["official_source_counts"]},
        "balance": "not applicable; SROIE is structured extraction without class labels",
        "checks": checks, "passed": passed,
        "hashes": {"evals_sha256": digest(root / "evals.csv"), "selection_sha256": digest(root / "selection.json"),
                   "source_snapshot_sha256": selection["sources"][0]["sha256"],
                   "case_manifest_sha256": case_manifest, "image_manifest_sha256": image_manifest},
        "selection": {"seed": selection["seed"], "rule": selection["selection_rule"],
                      "requested_counts": selection["requested_counts"]},
        "exclusions": dict(Counter(item["reason"] for item in selection.get("exclusions", []))),
        "failures": {"missing": missing, "hash_errors": hash_errors, "leakage": sorted(set(leakage)),
                     "boundary_errors": boundary_errors, "pilot_overlap_ids": pilot_overlap,
                     "pilot_image_overlap_ids": pilot_content_overlap},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--repeat", type=Path)
    parser.add_argument("--pilot-dataset", type=Path)
    parser.add_argument("--source-snapshot", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    proof = audit(args.dataset, args.repeat, args.pilot_dataset, args.source_snapshot)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": proof["passed"], **proof["counts"]}, sort_keys=True))
    return 0 if proof["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
