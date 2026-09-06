#!/usr/bin/env python3
"""Audit one terminal LEDGAR collection against the frozen plan and package."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SEEDS = (20260903, 20260904, 20260905)
STAGES = {"development": ("development", 500), "selection": ("validation", 1000),
          "final-test": ("test", 500)}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--results", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"output exists: {args.output}")
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    state = json.loads((args.run_dir / "collection-state.json").read_text(encoding="utf-8"))
    baseline_sop = args.run_dir / "packages/baseline-01/skills/ledgar-classification/SKILL.md"
    candidate_sop = args.run_dir / "packages/candidate-02/skills/ledgar-classification/SKILL.md"
    classifier = args.run_dir / "packages/candidate-02/classify.py"
    expected_sop = {"baseline": sha(baseline_sop), "hybrid": sha(candidate_sop)}
    expected_classifier = sha(classifier)
    expected_evals = sha(args.dataset / "evals.csv")
    expected_selection = sha(args.dataset / "selection.json")
    run_checks = []
    pair_checks = []
    rate_limits = 0
    failures = 0
    for stage, (split, cases) in STAGES.items():
        for seed in SEEDS:
            loaded = {}
            for arm in ("baseline", "hybrid"):
                path = args.results / f"valid-{stage}-repeat-{seed}-{arm}.json"
                run = json.loads(path.read_text(encoding="utf-8"))
                loaded[arm] = run
                receipts = list((path.parent / (path.name + ".attempts")).glob("*.json"))
                events = [json.loads(item.read_text(encoding="utf-8")) for item in receipts]
                rate_limits += sum(len(item.get("rate_limit_retries", [])) for item in events)
                failures += sum(item.get("status") == "failed" for item in events)
                ids = [item.get("id") for item in run.get("cases", [])]
                checks = {
                    "model_identity": run.get("model_identity") == plan["model"]["identity"],
                    "runtime_workers": run.get("runtime", {}).get("workers") == plan["runtime"]["workers"],
                    "split": run.get("split") == split,
                    "case_count": len(ids) == cases and len(set(ids)) == cases,
                    "evals_sha256": run.get("evals_sha256") == expected_evals,
                    "selection_sha256": run.get("invariants", {}).get("selection_sha256") == expected_selection,
                    "sop_sha256": run.get("sop_sha256") == expected_sop[arm],
                    "classifier_sha256": run.get("sop", {}).get("classifier_sha256") == (None if arm == "baseline" else expected_classifier),
                    "no_summary_errors": not run.get("summary", {}).get("errors"),
                    "receipts_complete": len(events) == cases and all(item.get("status") == "completed" for item in events),
                    "single_provider": run.get("observed_providers") == ["Google AI Studio"],
                }
                run_checks.append({"path": str(path), "stage": stage, "seed": seed,
                                   "arm": arm, "checks": checks, "passed": all(checks.values()),
                                   "summary": run.get("summary")})
            pair_equal = all(loaded["baseline"].get(key) == loaded["hybrid"].get(key)
                             for key in ("model", "model_identity", "seed", "evals", "evals_sha256", "runtime"))
            pair_equal = pair_equal and loaded["baseline"].get("invariants") == loaded["hybrid"].get("invariants")
            pair_equal = pair_equal and [c["id"] for c in loaded["baseline"]["cases"]] == [c["id"] for c in loaded["hybrid"]["cases"]]
            pair_checks.append({"stage": stage, "seed": seed, "paired_invariants_and_cases_match": pair_equal})
    selection_gates = []
    for seed in SEEDS:
        comparison = json.loads((args.run_dir / f"results/selection-repeat-{seed}-comparison.json").read_text(encoding="utf-8"))
        selection_gates.append({"seed": seed, "gate": comparison["gate"],
                                "passed": comparison["gate"].get("test_release_pass") is True})
    decisions = {key: (values[-1]["value"] if values else None)
                 for key, values in state["decisions"].items()}
    passed = (all(item["passed"] for item in run_checks)
              and all(item["paired_invariants_and_cases_match"] for item in pair_checks)
              and all(item["passed"] for item in selection_gates)
              and decisions == {"baseline-development": "ready", "candidate-development": "ready", "selection": "accept"}
              and state["stages"]["final-test"] == "complete" and failures == 0)
    result = {"schema_version": 1, "dataset": "ledgar", "plan_sha256": sha(args.plan),
              "git_head": state["git_head"], "model_identity": plan["model"]["identity"],
              "dataset_hashes": {"evals_sha256": expected_evals, "selection_sha256": expected_selection},
              "package_hashes": {"baseline_sop_sha256": expected_sop["baseline"],
                                 "candidate_sop_sha256": expected_sop["hybrid"],
                                 "classifier_sha256": expected_classifier},
              "decisions": decisions, "stages": state["stages"], "selection_gates": selection_gates,
              "pair_checks": pair_checks, "run_checks": run_checks,
              "rate_limit_retries": rate_limits, "failed_case_receipts": failures,
              "passed": passed}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"dataset": "ledgar", "runs": len(run_checks),
                      "rate_limit_retries": rate_limits, "passed": passed}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
