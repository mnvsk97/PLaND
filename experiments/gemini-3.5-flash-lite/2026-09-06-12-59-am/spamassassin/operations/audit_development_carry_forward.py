#!/usr/bin/env python3
"""Audit unchanged development evidence carried into the amended lineage."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


SEEDS = (20260903, 20260904, 20260905)


def rows(root: Path, split: str) -> list[dict[str, str]]:
    with (root / "evals.csv").open(encoding="utf-8", newline="") as handle:
        return [row for row in csv.DictReader(handle) if row["split"] == split]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dataset", required=True, type=Path)
    parser.add_argument("--amended-dataset", required=True, type=Path)
    parser.add_argument("--prior-run", required=True, type=Path)
    parser.add_argument("--current-run", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"output exists: {args.output}")
    old_dev = rows(args.base_dataset, "development")
    new_dev = rows(args.amended_dataset, "development")
    gate = json.loads((args.prior_run / "results/candidate-development-gate-01.json").read_text(encoding="utf-8"))
    runs = []
    for seed in SEEDS:
        for arm in ("baseline", "hybrid"):
            run_path = args.prior_run / f"results/development-repeat-{seed}-{arm}.json"
            run = json.loads(run_path.read_text(encoding="utf-8"))
            runs.append({"path": str(run_path), "seed": seed, "arm": arm,
                         "cases": run.get("summary", {}).get("cases"),
                         "accuracy": run.get("summary", {}).get("accuracy"),
                         "errors": run.get("summary", {}).get("errors")})
    package_checks = {}
    for package in ("baseline-01", "candidate-01"):
        old = args.prior_run / "packages" / package
        new = args.current_run / "packages" / package
        old_files = {path.relative_to(old).as_posix(): sha(path) for path in old.rglob("*") if path.is_file()}
        new_files = {path.relative_to(new).as_posix(): sha(path) for path in new.rglob("*") if path.is_file()}
        package_checks[package] = old_files == new_files
    checks = {
        "development_rows_identical": old_dev == new_dev and len(new_dev) == 500,
        "development_case_bytes_identical": all(
            sha(args.base_dataset / old["input"]) == sha(args.amended_dataset / new["input"])
            for old, new in zip(old_dev, new_dev, strict=True)
        ),
        "prior_candidate_gate_ready": gate.get("candidate") == "candidate-01" and gate.get("decision") == "ready",
        "six_complete_error_free_runs": len(runs) == 6
            and all(item["cases"] == 500 and not item["errors"] for item in runs),
        "packages_byte_identical": all(package_checks.values()),
    }
    result = {"schema_version": 1, "source_run": str(args.prior_run),
              "candidate": "candidate-01", "runs": runs,
              "package_checks": package_checks, "checks": checks,
              "baseline_decision": "ready", "candidate_decision": "ready",
              "passed": all(checks.values())}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": result["passed"], "runs": len(runs),
                      "baseline_decision": "ready", "candidate_decision": "ready"}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
