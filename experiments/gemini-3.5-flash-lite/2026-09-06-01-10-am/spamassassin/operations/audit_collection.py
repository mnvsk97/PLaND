#!/usr/bin/env python3
"""Audit the complete amendment-02 SpamAssassin evidence lineage."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


SEEDS = (20260903, 20260904, 20260905)
ARMS = ("baseline", "hybrid")
BLOCKED = {"mail-3125dcdc7726abc1c128", "mail-449598896e25273135c3"}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_digest(root: Path) -> dict[str, str]:
    return {path.relative_to(root).as_posix(): digest(path)
            for path in root.rglob("*") if path.is_file()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--original-run", required=True, type=Path)
    parser.add_argument("--amendment-01-run", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    results = args.run_dir / "results"
    with (args.dataset / "evals.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    split_counts = Counter(row["split"] for row in rows)
    validation_labels = Counter(json.loads(row["output"])["label"]
                                for row in rows if row["split"] == "validation")

    run_summaries = []
    output_runs_ok = True
    provider_ok = True
    for prefix, cases in (("selection", 1000), ("final-test", 500)):
        for seed in SEEDS:
            for arm in ARMS:
                path = results / f"{prefix}-repeat-{seed}-{arm}.json"
                run = load(path)
                summary = run["summary"]
                ok = (summary["cases"] == cases and summary["errors"] == {}
                      and summary["normal_completion_rate"] == 1.0
                      and len(run["cases"]) == cases)
                output_runs_ok &= ok
                provider_ok &= run.get("observed_providers") == ["Google AI Studio"]
                run_summaries.append({"path": str(path), "split": prefix, "seed": seed,
                                      "arm": arm, "cases": summary["cases"],
                                      "accuracy": summary["accuracy"],
                                      "total_tokens": summary["total_tokens"],
                                      "errors": summary["errors"], "passed": ok})

    comparison_checks = []
    comparisons_ok = True
    for prefix in ("selection", "final-test"):
        for seed in SEEDS:
            path = results / f"{prefix}-repeat-{seed}-comparison.json"
            comparison = load(path)
            ok = bool(comparison["gate"]["test_release_pass"])
            comparisons_ok &= ok
            comparison_checks.append({"path": str(path), "split": prefix, "seed": seed,
                                      "accuracy_difference_bootstrap_95":
                                          comparison["paired_statistics"]["accuracy_difference_bootstrap_95"],
                                      "token_reduction_bootstrap_95":
                                          comparison["paired_statistics"]["token_reduction_bootstrap_95"],
                                      "passed": ok})

    ledger = load(args.run_dir / "command-ledger.json")
    failed_events = [event for event in ledger["events"] if event.get("status") == "failed"]
    transient_receipts = []
    for event in failed_events:
        attempt_root = results / f"{event['name']}.json.attempts"
        receipts = [load(path) for path in attempt_root.glob("*.json")]
        failures = [item for item in receipts if item.get("status") == "failed"]
        transient_receipts.extend(failures)
    transient_ok = (len(failed_events) == 2 and len(transient_receipts) == 2
                    and all(item.get("error_type") == "OpenAIConnectionError"
                            and item.get("status_code") is None for item in transient_receipts)
                    and all((results / f"{event['name']}.json").exists() for event in failed_events))

    amendment_audit = load(results / "dataset-amendment-audit.json")
    development_audit = load(results / "development-carry-forward-audit.json")
    replacement_screen = load(results / "replacement-provider-screen.json")
    prior_screen = load(args.amendment_01_run / "results/selection-provider-block-screen.json")
    selection_gate = load(results / "selection-gate.json")
    package_checks = {
        name: tree_digest(args.run_dir / "packages" / name)
              == tree_digest(args.original_run / "packages" / name)
        for name in ("baseline-01", "candidate-01")
    }
    checks = {
        "exact_split_sizes": split_counts == {"development": 500, "validation": 1000, "test": 500},
        "selection_balance": validation_labels == {"ham": 500, "spam": 500},
        "known_blocked_cases_absent": not (BLOCKED & {row["id"] for row in rows}),
        "second_amendment_audit_passed": amendment_audit.get("passed") is True,
        "replacement_provider_screen_passed": replacement_screen.get("http_status") == 200
            and replacement_screen.get("choices_count") == 1 and replacement_screen.get("error_type") is None,
        "prior_full_selection_screen_passed": prior_screen.get("passed") is True
            and prior_screen.get("cases") == 1000
            and prior_screen.get("blocked_case_ids") == ["mail-449598896e25273135c3"],
        "development_carry_forward_passed": development_audit.get("passed") is True,
        "packages_byte_identical": all(package_checks.values()),
        "selection_gate_accepted": selection_gate.get("decision") == "accept"
            and selection_gate.get("final_test_released") is True,
        "twelve_complete_error_free_outputs": output_runs_ok,
        "all_six_comparisons_passed": comparisons_ok,
        "sole_provider_preserved": provider_ok,
        "transient_interruptions_preserved_and_resumed": transient_ok,
    }
    payload = {
        "schema_version": 1,
        "outcome": "complete",
        "selection_decision": "accept",
        "final_test_released": True,
        "counts": {"total": len(rows), "splits": dict(split_counts),
                   "selection_labels": dict(validation_labels)},
        "blocked_case_ids": sorted(BLOCKED),
        "replacement_case_ids": ["mail-023db858450b084e7238", "mail-0ae0fc25ca50549e73a8"],
        "failed_command_events": len(failed_events),
        "transient_failure_receipts": transient_receipts,
        "package_checks": package_checks,
        "checks": checks,
        "runs": run_summaries,
        "comparisons": comparison_checks,
        "passed": all(checks.values()),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": payload["passed"], "runs": len(run_summaries),
                      "comparisons": len(comparison_checks),
                      "transient_interruptions": len(transient_receipts)}))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
