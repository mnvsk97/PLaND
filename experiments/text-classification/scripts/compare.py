#!/usr/bin/env python3
"""Compare frozen NL and hybrid text-classification runs with paired statistics."""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from typing import Any, Callable


def macro_f1(cases: list[dict[str, Any]]) -> float:
    labels = sorted({case["expected"] for case in cases})
    scores = []
    for label in labels:
        true_positive = sum(
            case["expected"] == label and case["actual"] == label for case in cases
        )
        false_positive = sum(
            case["expected"] != label and case["actual"] == label for case in cases
        )
        false_negative = sum(
            case["expected"] == label and case["actual"] != label for case in cases
        )
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
        scores.append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)
    return sum(scores) / len(scores) if scores else 0.0


def normalized_summary(run: dict[str, Any]) -> dict[str, Any]:
    """Normalize either text or DeepAgent classification summaries."""
    summary = dict(run["summary"])
    summary.setdefault("macro_f1", macro_f1(run["cases"]))
    summary.setdefault("model_calls", len(run["cases"]))
    summary.setdefault("command_calls", 0)
    return summary


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> list[float]:
    if total <= 0:
        raise ValueError("total must be positive")
    proportion = successes / total
    denominator = 1 + z * z / total
    centre = (proportion + z * z / (2 * total)) / denominator
    radius = z * math.sqrt(
        proportion * (1 - proportion) / total + z * z / (4 * total * total)
    ) / denominator
    return [centre - radius, centre + radius]


def mcnemar_exact(nl_only: int, hybrid_only: int) -> float:
    discordant = nl_only + hybrid_only
    if discordant == 0:
        return 1.0
    tail = sum(math.comb(discordant, index) for index in range(min(nl_only, hybrid_only) + 1))
    return min(1.0, 2 * tail / (2 ** discordant))


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def paired_bootstrap(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
    statistic: Callable[[list[tuple[dict[str, Any], dict[str, Any]]]], float],
    samples: int,
    seed: int,
) -> list[float]:
    generator = random.Random(seed)
    estimates = []
    for _ in range(samples):
        resample = [pairs[generator.randrange(len(pairs))] for _ in pairs]
        estimates.append(statistic(resample))
    return [percentile(estimates, 0.025), percentile(estimates, 0.975)]


def accuracy_difference(pairs: list[tuple[dict[str, Any], dict[str, Any]]]) -> float:
    return sum(hybrid["correct"] - nl["correct"] for nl, hybrid in pairs) / len(pairs)


def token_reduction(pairs: list[tuple[dict[str, Any], dict[str, Any]]]) -> float:
    natural_language = sum(nl["total_tokens"] for nl, _ in pairs)
    hybrid = sum(candidate["total_tokens"] for _, candidate in pairs)
    return (natural_language - hybrid) / natural_language if natural_language else 0.0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nl", required=True, type=Path)
    parser.add_argument("--hybrid", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--bootstrap-samples", type=int, default=5000)
    parser.add_argument("--bootstrap-seed", type=int, default=20260902)
    parser.add_argument("--noninferiority-margin", type=float, default=0.02)
    parser.add_argument("--minimum-token-reduction", type=float, default=0.05)
    parser.add_argument("--minimum-accuracy", type=float, default=0.0)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"output exists: {args.output}")
    if args.bootstrap_samples < 1:
        raise SystemExit("--bootstrap-samples must be positive")

    nl, hybrid = (json.loads(path.read_text()) for path in (args.nl, args.hybrid))
    for key in ("split", "model", "model_digest", "seed"):
        if nl.get(key) != hybrid.get(key):
            raise SystemExit(f"invariant mismatch: {key}")
    for key in ("dataset", "evals_sha256"):
        if key in nl or key in hybrid:
            if nl.get(key) != hybrid.get(key):
                raise SystemExit(f"invariant mismatch: {key}")
    if nl.get("invariants") != hybrid.get("invariants"):
        raise SystemExit("invariant mismatch: frozen invariant set")

    nl_cases = {case["id"]: case for case in nl["cases"]}
    hybrid_cases = {case["id"]: case for case in hybrid["cases"]}
    if nl_cases.keys() != hybrid_cases.keys():
        raise SystemExit("case-id mismatch")
    pairs = []
    for identifier in sorted(nl_cases):
        natural_language = nl_cases[identifier]
        candidate = hybrid_cases[identifier]
        if natural_language["expected"] != candidate["expected"]:
            raise SystemExit(f"expected-output mismatch: {identifier}")
        pairs.append((natural_language, candidate))

    n_summary, h_summary = normalized_summary(nl), normalized_summary(hybrid)
    both_correct = sum(n["correct"] and h["correct"] for n, h in pairs)
    nl_only = sum(n["correct"] and not h["correct"] for n, h in pairs)
    hybrid_only = sum(not n["correct"] and h["correct"] for n, h in pairs)
    both_wrong = len(pairs) - both_correct - nl_only - hybrid_only
    accuracy_ci = paired_bootstrap(
        pairs, accuracy_difference, args.bootstrap_samples, args.bootstrap_seed,
    )
    token_ci = paired_bootstrap(
        pairs, token_reduction, args.bootstrap_samples, args.bootstrap_seed + 1,
    )
    observed_token_reduction = token_reduction(pairs)
    command_pairs = [(nl_case, hybrid_case) for nl_case, hybrid_case in pairs
                     if hybrid_case.get("source") == "command"]
    fallback_pairs = [(nl_case, hybrid_case) for nl_case, hybrid_case in pairs
                      if hybrid_case.get("source") != "command"]
    bypassed_nl_tokens = sum(nl_case["total_tokens"] for nl_case, _ in command_pairs)
    fallback_nl_tokens = sum(nl_case["total_tokens"] for nl_case, _ in fallback_pairs)
    fallback_hybrid_tokens = sum(hybrid_case["total_tokens"] for _, hybrid_case in fallback_pairs)
    total_tokens_saved = sum(nl_case["total_tokens"] for nl_case, _ in pairs) - sum(
        hybrid_case["total_tokens"] for _, hybrid_case in pairs
    )
    decision = {
        "quality_noninferior": accuracy_ci[0] >= -args.noninferiority_margin,
        "token_objective_met": (
            observed_token_reduction >= args.minimum_token_reduction and token_ci[0] > 0
        ),
        "absolute_viability": min(n_summary["accuracy"], h_summary["accuracy"]) >= args.minimum_accuracy,
    }
    decision["relative_pass"] = decision["quality_noninferior"] and decision["token_objective_met"]
    decision["test_release_pass"] = decision["relative_pass"] and decision["absolute_viability"]
    result = {
        "schema_version": 2,
        "natural_language": n_summary,
        "hybrid": h_summary,
        "delta_hybrid_minus_nl": {
            "accuracy": h_summary["accuracy"] - n_summary["accuracy"],
            "macro_f1": h_summary["macro_f1"] - n_summary["macro_f1"],
            "total_tokens": h_summary["total_tokens"] - n_summary["total_tokens"],
            "token_reduction_fraction": observed_token_reduction,
            "mean_latency_seconds": (
                h_summary["latency_seconds"]["mean"] - n_summary["latency_seconds"]["mean"]
            ),
            "model_calls": h_summary["model_calls"] - n_summary["model_calls"],
        },
        "paired_statistics": {
            "cases": len(pairs),
            "correctness_table": {
                "both_correct": both_correct,
                "natural_language_only": nl_only,
                "hybrid_only": hybrid_only,
                "both_wrong": both_wrong,
            },
            "natural_language_accuracy_wilson_95": wilson_interval(
                n_summary["correct"], n_summary["cases"]
            ),
            "hybrid_accuracy_wilson_95": wilson_interval(
                h_summary["correct"], h_summary["cases"]
            ),
            "accuracy_difference_bootstrap_95": accuracy_ci,
            "token_reduction_bootstrap_95": token_ci,
            "mcnemar_exact_p": mcnemar_exact(nl_only, hybrid_only),
            "bootstrap_samples": args.bootstrap_samples,
            "bootstrap_seed": args.bootstrap_seed,
        },
        "mechanism_decomposition": {
            "command_routed_cases": len(command_pairs),
            "model_fallback_cases": len(fallback_pairs),
            "natural_language_tokens_on_command_routed_cases": bypassed_nl_tokens,
            "hybrid_tokens_on_command_routed_cases": 0,
            "natural_language_tokens_on_model_fallback_cases": fallback_nl_tokens,
            "hybrid_tokens_on_model_fallback_cases": fallback_hybrid_tokens,
            "tokens_saved_total": total_tokens_saved,
            "tokens_saved_by_bypassing_model_calls": bypassed_nl_tokens,
            "tokens_saved_on_model_fallback_cases": fallback_nl_tokens - fallback_hybrid_tokens,
            "command_routed_hybrid_accuracy": (
                sum(hybrid_case["correct"] for _, hybrid_case in command_pairs) / len(command_pairs)
                if command_pairs else None
            ),
            "natural_language_accuracy_on_same_command_routed_cases": (
                sum(nl_case["correct"] for nl_case, _ in command_pairs) / len(command_pairs)
                if command_pairs else None
            ),
        },
        "gate": {
            "noninferiority_margin": args.noninferiority_margin,
            "minimum_token_reduction": args.minimum_token_reduction,
            "minimum_accuracy": args.minimum_accuracy,
            **decision,
        },
        "invariants": nl["invariants"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"delta": result["delta_hybrid_minus_nl"], "gate": decision}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
