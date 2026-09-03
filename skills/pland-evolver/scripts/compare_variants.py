#!/usr/bin/env python3
"""Save a deterministic NL-versus-hybrid PLaND metric comparison."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--natural-language-run", required=True, type=Path)
    parser.add_argument("--hybrid-run", required=True, type=Path)
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


def metrics(run: dict[str, Any]) -> dict[str, Any]:
    summary = run["summary"]
    latency = summary["latency_seconds"]
    quality = summary.get("quality", summary.get("accuracy"))
    if quality is None:
        raise ValueError("run summary must contain quality")
    result = {
        "quality": quality,
        "quality_metric": run.get("quality_metric") or summary.get("quality_metric") or "accuracy",
        "correct": summary.get("correct"),
        "cases": summary.get("cases"),
        "input_tokens": summary.get("input_tokens", 0),
        "output_tokens": summary.get("output_tokens", 0),
        "total_tokens": summary["total_tokens"],
        "estimated_model_cost_usd": summary.get("estimated_model_cost_usd", 0.0),
        "errors": summary.get("errors", {}),
        "normal_completion_rate": summary.get("normal_completion_rate"),
        "escape_count": summary.get("escape_count", 0),
        "escape_rate": summary.get("escape_rate", 0.0),
        "latency_seconds": {
            "total": latency.get("total"),
            "mean": latency["mean"],
            "p95": latency.get("p95"),
        },
    }
    if "accuracy" in summary:
        result["accuracy"] = summary["accuracy"]
    return result


def compare(natural: dict[str, Any], hybrid: dict[str, Any]) -> dict[str, Any]:
    mismatches = []
    for field in ("model", "model_digest", "seed", "evals", "split"):
        if natural.get(field) != hybrid.get(field):
            mismatches.append(field)
    if mismatches:
        raise ValueError("incomparable run invariants: " + ", ".join(mismatches))
    for run, expected in ((natural, "baseline"), (hybrid, None)):
        for field in ("experiment_id", "run_id", "candidate_id", "attempt"):
            if run.get(field) in (None, ""):
                raise ValueError(f"missing run identity: {field}")
        if expected and run["candidate_id"] != expected:
            raise ValueError("natural-language candidate identity must be baseline")
    if hybrid["candidate_id"] == "baseline":
        raise ValueError("hybrid candidate identity must not be baseline")
    for run in (natural, hybrid):
        for field in ("sop_sha256", "skill_content_sha256", "frozen_manifest_sha256"):
            value = run.get(field) or run.get("sop", {}).get(field.removeprefix("sop_"))
            if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError(f"invalid full hash: {field}")
    frozen_fields = (
        "system_prompt_sha256",
        "agent_harness_sha256",
        "datasource_snapshot_sha256",
        "scorer_sha256",
    )
    natural_invariants = natural.get("invariants", {})
    hybrid_invariants = hybrid.get("invariants", {})
    frozen_mismatches = [
        field
        for field in frozen_fields
        if not natural_invariants.get(field)
        or natural_invariants.get(field) != hybrid_invariants.get(field)
    ]
    if frozen_mismatches:
        raise ValueError("incomparable frozen invariants: " + ", ".join(frozen_mismatches))
    natural_evaluation = evaluation_fingerprint(natural)
    hybrid_evaluation = evaluation_fingerprint(hybrid)
    if not natural_evaluation or natural_evaluation != hybrid_evaluation:
        raise ValueError("incomparable frozen invariants: evaluation_sha256")
    if "sop" not in natural or "sop" not in hybrid:
        raise ValueError("both runs must contain an SOP snapshot")
    natural_steps = natural["sop"]["step_representations"]
    hybrid_steps = hybrid["sop"]["step_representations"]
    if natural_steps.get("command", 0) != 0:
        raise ValueError("natural-language run contains command steps")
    if hybrid_steps.get("command", 0) < 1:
        raise ValueError("hybrid run must contain at least one command step")
    natural_cases = natural.get("cases")
    hybrid_cases = hybrid.get("cases")
    if natural_cases is not None or hybrid_cases is not None:
        if natural_cases is None or hybrid_cases is None:
            raise ValueError("both runs must include case records")
        def indexed(cases: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
            result = {str(case.get("id", "")): case for case in cases}
            if "" in result or len(result) != len(cases):
                raise ValueError("missing or duplicate case IDs")
            return result
        if set(indexed(natural_cases)) != set(indexed(hybrid_cases)):
            raise ValueError("case ID mismatch")

    natural_metrics = metrics(natural)
    hybrid_metrics = metrics(hybrid)
    if natural_metrics["quality_metric"] != hybrid_metrics["quality_metric"]:
        raise ValueError("incomparable run invariants: quality_metric")
    natural_tokens = natural_metrics["total_tokens"]
    natural_latency = natural_metrics["latency_seconds"]["mean"]
    baseline_model_tokens = natural["summary"].get("model_tokens", natural_tokens)
    candidate_model_tokens = hybrid["summary"].get("model_tokens", hybrid_metrics["total_tokens"])
    fallback_model_tokens = hybrid["summary"].get("fallback_model_tokens", 0)
    determinisation = (
        max(0, baseline_model_tokens - candidate_model_tokens - fallback_model_tokens) / baseline_model_tokens
        if baseline_model_tokens else None
    )
    return {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "comparison": "natural_language_vs_hybrid",
        "invariants": {
            **{field: natural.get(field) for field in ("model", "model_digest", "seed", "evals", "evals_sha256", "split")},
            **natural_invariants,
        },
        "natural_language": {"sop": natural["sop"], "metrics": natural_metrics},
        "hybrid": {"sop": hybrid["sop"], "metrics": hybrid_metrics},
        "identity": {
            "experiment_id": natural["experiment_id"],
            "baseline_run_id": natural["run_id"],
            "candidate_run_id": hybrid["run_id"],
            "candidate_id": hybrid["candidate_id"],
            "baseline_sop_sha256": natural.get("sop_sha256", natural["sop"].get("sha256")),
            "candidate_sop_sha256": hybrid.get("sop_sha256", hybrid["sop"].get("sha256")),
            "baseline_skill_content_sha256": natural["skill_content_sha256"],
            "candidate_skill_content_sha256": hybrid["skill_content_sha256"],
        },
        "cost_weighted_determinisation": {
            "baseline_model_tokens": baseline_model_tokens,
            "candidate_model_tokens": candidate_model_tokens,
            "fallback_model_tokens": fallback_model_tokens,
            "rate": determinisation,
        },
        "delta_hybrid_minus_natural_language": {
            "quality": hybrid_metrics["quality"] - natural_metrics["quality"],
            "input_tokens": hybrid_metrics["input_tokens"] - natural_metrics["input_tokens"],
            "output_tokens": hybrid_metrics["output_tokens"] - natural_metrics["output_tokens"],
            "total_tokens": hybrid_tokens - natural_tokens if (hybrid_tokens := hybrid_metrics["total_tokens"]) is not None else None,
            "total_token_ratio": hybrid_metrics["total_tokens"] / natural_tokens if natural_tokens else None,
            "estimated_model_cost_usd": hybrid_metrics["estimated_model_cost_usd"] - natural_metrics["estimated_model_cost_usd"],
            "mean_latency_seconds": hybrid_metrics["latency_seconds"]["mean"] - natural_latency,
            "mean_latency_ratio": hybrid_metrics["latency_seconds"]["mean"] / natural_latency if natural_latency else None,
            **(
                {"accuracy_points": hybrid_metrics["accuracy"] - natural_metrics["accuracy"]}
                if "accuracy" in hybrid_metrics and "accuracy" in natural_metrics else {}
            ),
        },
    }


def main() -> int:
    args = parse_args()
    if args.output.exists():
        raise SystemExit(f"output already exists: {args.output}")
    try:
        result = compare(load(args.natural_language_run), load(args.hybrid_run))
    except (KeyError, TypeError, ValueError) as error:
        raise SystemExit(str(error)) from error
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["delta_hybrid_minus_natural_language"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
