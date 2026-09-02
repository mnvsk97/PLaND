#!/usr/bin/env python3
"""Audit saved text-classification runs against current frozen artifacts.

This is explicitly a post-run evidence audit. It strengthens reproducibility
without pretending that fields absent from the original run payload were
preregistered or enforced at runtime.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--experiment", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    harness = Path(__file__).with_name("run_experiment.py")
    expected_fixed = {
        "system_prompt_sha256": digest(args.experiment / "system-prompt.md"),
        "evals_sha256": digest(args.dataset / "evals.csv"),
        "selection_sha256": digest(args.dataset / "selection.json"),
        "scorer_sha256": digest(harness),
        "agent_harness_sha256": digest(harness),
    }
    run_files = sorted(
        path for path in (args.experiment / "results").glob("confirmatory-*.json")
        if "comparison" not in path.name and "audit" not in path.name
    )
    checks, contracts = [], {}
    for path in run_files:
        run = json.loads(path.read_text(encoding="utf-8"))
        variant = "hybrid" if path.stem.endswith("-hybrid") else "natural_language"
        sop_path = args.experiment / ("hybrid" if variant == "hybrid" else "nl") / "SKILL.md"
        invariant_match = run.get("invariants") == expected_fixed
        sop_match = run.get("sop", {}).get("sha256") == digest(sop_path)
        check = {
            "path": path.relative_to(args.experiment).as_posix(),
            "variant": variant,
            "fixed_invariants_match_current_files": invariant_match,
            "sop_snapshot_matches_current_skill": sop_match,
        }
        checks.append(check)
        key = (str(run.get("split")), variant)
        contracts[key] = {
            "model": run.get("model"),
            "model_digest": run.get("model_digest"),
            "seed": run.get("seed"),
            "invariants": run.get("invariants"),
        }

    paired_equal = True
    for split in {key[0] for key in contracts}:
        natural = contracts.get((split, "natural_language"))
        hybrid = contracts.get((split, "hybrid"))
        if natural and hybrid:
            paired_equal &= natural == hybrid

    classifier = args.experiment / "hybrid" / "classify.py"
    package_files = [args.experiment / "hybrid" / "SKILL.md"]
    if classifier.is_file():
        package_files.append(classifier)
    pyproject = args.experiment / "pyproject.toml"
    if pyproject.is_file():
        package_files.append(pyproject)
    payload = {
        "schema_version": 1,
        "audit_timing": "post_run",
        "scope_note": "harness-level realization of hybrid SOP routing; not autonomous DeepAgent execution",
        "runtime_boundary": {
            "model_endpoint": "http://127.0.0.1:11434",
            "paid_services": False,
            "model_options_are_embodied_in_harness_hash": True,
        },
        "fixed_artifacts": expected_fixed,
        "allowed_hybrid_package": {
            path.relative_to(args.experiment).as_posix(): digest(path) for path in package_files
        },
        "checks": checks,
        "paired_run_contracts_equal": paired_equal,
        "passed": bool(run_files) and paired_equal and all(
            item["fixed_invariants_match_current_files"]
            and item["sop_snapshot_matches_current_skill"] for item in checks
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"runs": len(checks), "passed": payload["passed"]}))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
