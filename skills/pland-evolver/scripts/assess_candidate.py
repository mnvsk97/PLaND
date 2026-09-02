#!/usr/bin/env python3
"""Deterministically accept or reject a PLaND candidate from frozen run files."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-development", required=True, type=Path)
    parser.add_argument("--candidate-development", required=True, type=Path)
    parser.add_argument("--candidate-validation", type=Path)
    parser.add_argument("--baseline-validation", type=Path)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--hypothesis", required=True)
    parser.add_argument("--iteration", type=int, default=1, help="One-based candidate iteration")
    parser.add_argument("--max-iterations", type=int, default=10)
    parser.add_argument("--target-accuracy", required=True, type=float)
    parser.add_argument(
        "--optimization-metric",
        choices=("total_tokens", "mean_latency_seconds", "estimated_model_cost_usd"),
        default="total_tokens",
    )
    parser.add_argument("--min-objective-improvement-ratio", type=float, default=0.0)
    parser.add_argument("--require-hybrid-sop", action="store_true")
    parser.add_argument("--max-validation-latency-ratio", type=float, default=2.0)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluation_fingerprint(run: dict[str, Any]) -> str | None:
    invariants = run.get("invariants", {})
    values = {
        value
        for value in (
            invariants.get("evaluation_sha256"),
            invariants.get("evals_sha256"),
            run.get("evals_sha256"),
        )
        if value
    }
    return next(iter(values)) if len(values) == 1 else None


def comparable(left: dict[str, Any], right: dict[str, Any]) -> list[str]:
    failures = []
    for field in ("model", "model_digest", "seed", "evals"):
        if left.get(field) != right.get(field):
            failures.append(f"invariant_mismatch:{field}")
    required = (
        "system_prompt_sha256",
        "agent_harness_sha256",
        "datasource_snapshot_sha256",
        "scorer_sha256",
    )
    left_invariants = left.get("invariants", {})
    right_invariants = right.get("invariants", {})
    for field in required:
        if not left_invariants.get(field) or left_invariants.get(field) != right_invariants.get(field):
            failures.append(f"invariant_mismatch:{field}")
    left_evaluation = evaluation_fingerprint(left)
    right_evaluation = evaluation_fingerprint(right)
    if not left_evaluation or left_evaluation != right_evaluation:
        failures.append("invariant_mismatch:evaluation_sha256")
    return failures


def metric_delta(candidate: dict[str, Any], baseline: dict[str, Any]) -> dict[str, float]:
    candidate_summary = candidate["summary"]
    baseline_summary = baseline["summary"]
    return {
        "accuracy_points": candidate_summary["accuracy"] - baseline_summary["accuracy"],
        "tokens": candidate_summary["total_tokens"] - baseline_summary["total_tokens"],
        "token_ratio": candidate_summary["total_tokens"] / baseline_summary["total_tokens"] if baseline_summary["total_tokens"] else 0.0,
        "mean_latency_seconds": candidate_summary["latency_seconds"]["mean"] - baseline_summary["latency_seconds"]["mean"],
        "mean_latency_ratio": candidate_summary["latency_seconds"]["mean"] / baseline_summary["latency_seconds"]["mean"] if baseline_summary["latency_seconds"]["mean"] else 0.0,
    }


def objective_value(run: dict[str, Any], metric: str) -> float:
    summary = run["summary"]
    if metric == "mean_latency_seconds":
        return float(summary["latency_seconds"]["mean"])
    return float(summary[metric])


def objective_improved(
    candidate: dict[str, Any], baseline: dict[str, Any], metric: str, minimum_ratio: float
) -> bool:
    baseline_value = objective_value(baseline, metric)
    candidate_value = objective_value(candidate, metric)
    if baseline_value == 0:
        return candidate_value < baseline_value
    if minimum_ratio == 0:
        return candidate_value < baseline_value
    return candidate_value <= baseline_value * (1 - minimum_ratio)


def assess(args: argparse.Namespace) -> dict[str, Any]:
    baseline_development = load(args.baseline_development)
    candidate_development = load(args.candidate_development)
    checks = comparable(baseline_development, candidate_development)
    if baseline_development.get("split") != "development" or candidate_development.get("split") != "development":
        checks.append("invalid_development_split")
    candidate_accuracy = candidate_development["summary"]["accuracy"]
    if candidate_accuracy < args.target_accuracy:
        checks.append("development_below_accuracy_floor")
    if candidate_development["summary"].get("errors"):
        checks.append("development_errors")
    if not objective_improved(
        candidate_development,
        baseline_development,
        args.optimization_metric,
        args.min_objective_improvement_ratio,
    ):
        checks.append("development_objective_not_improved")
    if args.require_hybrid_sop and candidate_development.get("sop", {}).get("variant") != "hybrid":
        checks.append("development_sop_not_hybrid")

    result: dict[str, Any] = {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "candidate": args.candidate,
        "hypothesis": args.hypothesis,
        "iteration": args.iteration,
        "max_iterations": args.max_iterations,
        "target_accuracy": args.target_accuracy,
        "optimization_metric": args.optimization_metric,
        "min_objective_improvement_ratio": args.min_objective_improvement_ratio,
        "require_hybrid_sop": args.require_hybrid_sop,
        "frozen_invariants": baseline_development.get("invariants"),
        "system_prompt": baseline_development.get("system_prompt"),
        "development": {
            "baseline": baseline_development["summary"],
            "candidate": candidate_development["summary"],
            "delta": metric_delta(candidate_development, baseline_development),
        },
        "validation": None,
        "failed_checks": checks,
    }
    if args.iteration > args.max_iterations:
        result["failed_checks"].append("iteration_limit_exceeded")
        result["decision"] = "stop_iteration_limit"
        return result
    if checks:
        result["decision"] = "reject_before_validation"
        return result
    if args.candidate_validation is None:
        result["decision"] = "eligible_for_validation"
        return result

    candidate_validation = load(args.candidate_validation)
    validation_checks = comparable(candidate_development, candidate_validation)
    if candidate_validation.get("split") != "validation":
        validation_checks.append("invalid_validation_split")
    if candidate_validation["summary"]["accuracy"] < args.target_accuracy:
        validation_checks.append("validation_below_target")
    if candidate_validation["summary"].get("errors"):
        validation_checks.append("validation_errors")
    if args.require_hybrid_sop and candidate_validation.get("sop", {}).get("variant") != "hybrid":
        validation_checks.append("validation_sop_not_hybrid")

    validation_result: dict[str, Any] = {"candidate": candidate_validation["summary"]}
    if args.baseline_validation is None:
        validation_checks.append("missing_baseline_validation")
    else:
        baseline_validation = load(args.baseline_validation)
        if baseline_validation.get("split") != "validation":
            validation_checks.append("invalid_baseline_validation_split")
        validation_checks.extend(comparable(candidate_validation, baseline_validation))
        latency_ratio = (
            candidate_validation["summary"]["latency_seconds"]["mean"]
            / baseline_validation["summary"]["latency_seconds"]["mean"]
        )
        if latency_ratio > args.max_validation_latency_ratio:
            validation_checks.append("validation_latency_guardrail")
        if candidate_validation["summary"]["total_tokens"] > baseline_validation["summary"]["total_tokens"]:
            validation_checks.append("validation_token_regression")
        if not objective_improved(
            candidate_validation,
            baseline_validation,
            args.optimization_metric,
            args.min_objective_improvement_ratio,
        ):
            validation_checks.append("validation_objective_not_improved")
        validation_result["baseline"] = baseline_validation["summary"]
        validation_result["delta"] = metric_delta(candidate_validation, baseline_validation)

    result["validation"] = validation_result
    result["failed_checks"].extend(validation_checks)
    result["decision"] = "accept" if not result["failed_checks"] else "reject_after_validation"
    return result


def main() -> int:
    args = parse_args()
    if not 0 <= args.target_accuracy <= 1:
        raise SystemExit("--target-accuracy must be between 0 and 1")
    if args.max_validation_latency_ratio <= 0:
        raise SystemExit("--max-validation-latency-ratio must be positive")
    if args.iteration <= 0:
        raise SystemExit("--iteration must be positive")
    if args.max_iterations <= 0:
        raise SystemExit("--max-iterations must be positive")
    if not 0 <= args.min_objective_improvement_ratio < 1:
        raise SystemExit("--min-objective-improvement-ratio must be between 0 and 1")
    if args.output.exists():
        raise SystemExit(f"output already exists: {args.output}")
    result = assess(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"candidate": result["candidate"], "decision": result["decision"], "failed_checks": result["failed_checks"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
