#!/usr/bin/env python3
"""Audit terminal SpamAssassin evidence after a provider-blocked selection case."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SEEDS = (20260903, 20260904, 20260905)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"output exists: {args.output}")
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    state = json.loads((args.run_dir / "collection-state.json").read_text(encoding="utf-8"))
    assessment = json.loads((args.run_dir / "results/selection-terminal-assessment.json").read_text(encoding="utf-8"))
    baseline_sop = args.run_dir / "packages/baseline-01/skills/spamassassin-classification/SKILL.md"
    candidate_sop = args.run_dir / "packages/candidate-01/skills/spamassassin-classification/SKILL.md"
    classifier = args.run_dir / "packages/candidate-01/classify.py"
    expected_sop = {"baseline": sha(baseline_sop), "hybrid": sha(candidate_sop)}
    expected_evals = sha(args.dataset / "evals.csv")
    expected_selection = sha(args.dataset / "selection.json")
    expected_classifier = sha(classifier)
    run_checks = []
    pair_checks = []
    rate_limits = 0
    for seed in SEEDS:
        loaded = {}
        for arm in ("baseline", "hybrid"):
            path = args.run_dir / f"results/development-repeat-{seed}-{arm}.json"
            run = json.loads(path.read_text(encoding="utf-8"))
            loaded[arm] = run
            receipts = [json.loads(item.read_text(encoding="utf-8"))
                        for item in (path.parent / (path.name + ".attempts")).glob("*.json")]
            rate_limits += sum(len(item.get("rate_limit_retries", [])) for item in receipts)
            ids = [item.get("id") for item in run.get("cases", [])]
            checks = {
                "model_identity": run.get("model_identity") == plan["model"]["identity"],
                "runtime_workers": run.get("runtime", {}).get("workers") == plan["runtime"]["workers"],
                "split": run.get("split") == "development",
                "case_count": len(ids) == 500 and len(set(ids)) == 500,
                "evals_sha256": run.get("evals_sha256") == expected_evals,
                "selection_sha256": run.get("invariants", {}).get("selection_sha256") == expected_selection,
                "sop_sha256": run.get("sop_sha256") == expected_sop[arm],
                "classifier_sha256": run.get("sop", {}).get("classifier_sha256")
                    == (None if arm == "baseline" else expected_classifier),
                "no_summary_errors": not run.get("summary", {}).get("errors"),
                "receipts_complete": len(receipts) == 500
                    and all(item.get("status") == "completed" for item in receipts),
                "single_provider": run.get("observed_providers") == ["Google AI Studio"],
            }
            run_checks.append({"path": str(path), "seed": seed, "arm": arm,
                               "checks": checks, "passed": all(checks.values()),
                               "summary": run.get("summary")})
        paired = all(loaded["baseline"].get(key) == loaded["hybrid"].get(key)
                     for key in ("model", "model_identity", "seed", "evals", "evals_sha256", "runtime"))
        paired = paired and loaded["baseline"].get("invariants") == loaded["hybrid"].get("invariants")
        paired = paired and [item["id"] for item in loaded["baseline"]["cases"]] == [item["id"] for item in loaded["hybrid"]["cases"]]
        pair_checks.append({"stage": "development", "seed": seed,
                            "paired_invariants_and_cases_match": paired})
    interrupted = []
    for path in (args.run_dir / "interrupted-runs").glob("**/*.json"):
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("status") == "failed":
            interrupted.append({"path": str(path), "case_id": value.get("case_id"),
                                "error_type": value.get("error_type")})
    decisions = {key: (values[-1]["value"] if values else None)
                 for key, values in state["decisions"].items()}
    final_files = list((args.run_dir / "results").glob("final-test-repeat-*.json"))
    terminal_checks = {
        "development_ready": decisions["candidate-development"] == "ready",
        "selection_rejected": decisions["selection"] == "reject",
        "selection_assessment_rejects": assessment.get("decision") == "reject",
        "no_errors_gate_failed": assessment.get("gates", {}).get("paired_no_errors") is False,
        "provider_block_verified": assessment.get("checks", {}).get("terminal_provider_block") is True,
        "not_rate_limit_verified": assessment.get("checks", {}).get("not_rate_limited") is True,
        "final_test_pending": state["stages"]["final-test"] == "pending",
        "final_test_unopened": not final_files,
        "partial_selection_preserved": (args.run_dir / "results/selection-repeat-20260903-baseline.json.partial.json").is_file(),
        "failed_attempts_preserved": len(interrupted) >= 5,
    }
    passed = (all(item["passed"] for item in run_checks)
              and all(item["paired_invariants_and_cases_match"] for item in pair_checks)
              and all(terminal_checks.values())
              and decisions["baseline-development"] == "ready")
    result = {
        "schema_version": 1,
        "dataset": "spamassassin",
        "collection_outcome": "failed_selection_provider_block",
        "plan_sha256": sha(args.plan),
        "git_head": state["git_head"],
        "model_identity": plan["model"]["identity"],
        "dataset_hashes": {"evals_sha256": expected_evals, "selection_sha256": expected_selection},
        "package_hashes": {"baseline_sop_sha256": expected_sop["baseline"],
                           "candidate_sop_sha256": expected_sop["hybrid"],
                           "classifier_sha256": expected_classifier},
        "decisions": decisions,
        "stages": state["stages"],
        "terminal_selection_assessment": assessment,
        "terminal_checks": terminal_checks,
        "pair_checks": pair_checks,
        "run_checks": run_checks,
        "rate_limit_retries": rate_limits,
        "preserved_failed_receipts": interrupted,
        "final_test_unopened": True,
        "passed": passed,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"dataset": "spamassassin", "collection_outcome": result["collection_outcome"],
                      "development_runs": len(run_checks), "preserved_failures": len(interrupted),
                      "final_test_unopened": True, "passed": passed}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
