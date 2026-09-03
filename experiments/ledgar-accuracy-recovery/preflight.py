#!/usr/bin/env python3
"""Dry-run the LEDGAR accuracy-recovery protocol without selecting or running cases."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
REPOSITORY = HERE.parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def capacity(protocol: dict[str, Any], proof: dict[str, Any]) -> dict[str, Any]:
    dataset = protocol["dataset"]
    classes = int(dataset["classes"])
    requested = dataset["splits"]
    prior = proof["requested_split_counts"]
    labels = list(load(REPOSITORY / dataset["prior_selection"])["eligible_unique_by_label"])
    source_for = proof["source_split_mapping"]
    eligible = proof["eligible_unique_by_label_and_source_split"]
    details = {}
    feasible = True
    for split, count in requested.items():
        if count % classes:
            details[split] = {"requested": count, "feasible": False, "reason": "not_balanced"}
            feasible = False
            continue
        requested_per_label = count // classes
        prior_per_label = int(prior[split]) // classes
        source_split = source_for[split]
        remaining = {label: int(eligible[source_split][label]) - prior_per_label for label in labels}
        limiting_label = min(remaining, key=remaining.get)
        split_feasible = remaining[limiting_label] >= requested_per_label
        feasible = feasible and split_feasible
        details[split] = {
            "requested": count,
            "requested_per_label": requested_per_label,
            "limiting_label": limiting_label,
            "limiting_remaining_per_label": remaining[limiting_label],
            "maximum_balanced_cases": remaining[limiting_label] * classes,
            "feasible": split_feasible,
        }
    return {"feasible": feasible, "splits": details}


def command_output(command: list[str]) -> tuple[int, str]:
    completed = subprocess.run(command, cwd=REPOSITORY, text=True, capture_output=True)
    return completed.returncode, (completed.stdout + completed.stderr).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=HERE / "protocol.json")
    parser.add_argument("--source-dir", type=Path, help="Directory containing pinned train/validation/test JSONL")
    args = parser.parse_args()

    protocol = load(args.protocol)
    proof_path = REPOSITORY / protocol["dataset"]["capacity_proof"]
    prior_path = REPOSITORY / protocol["dataset"]["prior_selection"]
    checks: list[dict[str, Any]] = []

    proof = load(proof_path)
    capacity_result = capacity(protocol, proof)
    checks.append({"name": "fresh_balanced_capacity", "status": "pass" if capacity_result["feasible"] else "block", "detail": capacity_result})

    compare_path = REPOSITORY / "experiments/text-classification/scripts/compare.py"
    _, help_text = command_output(["python3", str(compare_path), "--help"])
    required_flags = (
        "--require-no-accuracy-regression",
        "--minimum-accuracy-difference-lower-bound",
        "--max-per-label-recall-drop",
        "--minimum-command-precision",
    )
    missing_flags = [flag for flag in required_flags if flag not in help_text]
    checks.append({"name": "strict_gate_support", "status": "pass" if not missing_flags else "block", "missing": missing_flags})

    model = protocol["runtime"]["model"]
    expected_digest = protocol["runtime"]["model_digest"]
    ollama = shutil.which("ollama")
    model_ready = False
    model_detail = "ollama executable not found"
    if ollama:
        code, listing = command_output([ollama, "list"])
        model_detail = listing
        if code == 0:
            model_ready = any(
                line.split()[:2] == [model, expected_digest[:12]]
                for line in listing.splitlines()[1:]
            )
    checks.append({"name": "frozen_model", "status": "pass" if model_ready else "block", "detail": model_detail})

    expected_sources = {item["path"]: item for item in load(prior_path)["sources"]}
    if args.source_dir is None:
        checks.append({"name": "pinned_source_files", "status": "block", "detail": "Pass --source-dir with the pinned LEDGAR train.jsonl, validation.jsonl, and test.jsonl files."})
    else:
        source_checks = []
        for name, expected in expected_sources.items():
            path = args.source_dir / name
            source_checks.append({
                "path": name,
                "exists": path.is_file(),
                "sha256_matches": path.is_file() and sha256(path) == expected["sha256"],
            })
        source_ready = all(item["exists"] and item["sha256_matches"] for item in source_checks)
        checks.append({"name": "pinned_source_files", "status": "pass" if source_ready else "block", "detail": source_checks})

    _, git_status = command_output(["git", "status", "--porcelain"])
    checks.append({"name": "clean_frozen_commit", "status": "pass" if not git_status else "warn", "detail": git_status or "clean"})
    _, git_head = command_output(["git", "rev-parse", "HEAD"])

    blockers = [check["name"] for check in checks if check["status"] == "block"]
    result = {
        "schema_version": 1,
        "mode": "dry_run",
        "protocol": protocol["name"],
        "git_head": git_head,
        "status": "ready" if not blockers else "blocked",
        "blockers": blockers,
        "checks": checks,
        "side_effects": "No dataset was selected, no holdout labels were opened, and no model inference was run."
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not blockers else 2


if __name__ == "__main__":
    raise SystemExit(main())
