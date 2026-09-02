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


def metrics(run: dict[str, Any]) -> dict[str, Any]:
    summary = run["summary"]
    latency = summary["latency_seconds"]
    return {
        "accuracy": summary["accuracy"],
        "correct": summary.get("correct"),
        "cases": summary.get("cases"),
        "input_tokens": summary.get("input_tokens", 0),
        "output_tokens": summary.get("output_tokens", 0),
        "total_tokens": summary["total_tokens"],
        "estimated_model_cost_usd": summary.get("estimated_model_cost_usd", 0.0),
        "latency_seconds": {
            "total": latency.get("total"),
            "mean": latency["mean"],
            "p95": latency.get("p95"),
        },
    }


def compare(natural: dict[str, Any], hybrid: dict[str, Any]) -> dict[str, Any]:
    mismatches = []
    for field in ("model", "model_digest", "seed", "evals", "evals_sha256", "split"):
        if natural.get(field) != hybrid.get(field):
            mismatches.append(field)
    if mismatches:
        raise ValueError("incomparable run invariants: " + ", ".join(mismatches))
    frozen_fields = (
        "system_prompt_sha256",
        "agent_harness_sha256",
        "datasource_snapshot_sha256",
        "evaluation_sha256",
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
    if "sop" not in natural or "sop" not in hybrid:
        raise ValueError("both runs must contain an SOP snapshot")
    natural_steps = natural["sop"]["step_representations"]
    hybrid_steps = hybrid["sop"]["step_representations"]
    if natural_steps.get("command", 0) != 0:
        raise ValueError("natural-language run contains command steps")
    if hybrid_steps.get("command", 0) < 1:
        raise ValueError("hybrid run must contain at least one command step")

    natural_metrics = metrics(natural)
    hybrid_metrics = metrics(hybrid)
    natural_tokens = natural_metrics["total_tokens"]
    natural_latency = natural_metrics["latency_seconds"]["mean"]
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
        "delta_hybrid_minus_natural_language": {
            "accuracy_points": hybrid_metrics["accuracy"] - natural_metrics["accuracy"],
            "input_tokens": hybrid_metrics["input_tokens"] - natural_metrics["input_tokens"],
            "output_tokens": hybrid_metrics["output_tokens"] - natural_metrics["output_tokens"],
            "total_tokens": hybrid_tokens - natural_tokens if (hybrid_tokens := hybrid_metrics["total_tokens"]) is not None else None,
            "total_token_ratio": hybrid_metrics["total_tokens"] / natural_tokens if natural_tokens else None,
            "estimated_model_cost_usd": hybrid_metrics["estimated_model_cost_usd"] - natural_metrics["estimated_model_cost_usd"],
            "mean_latency_seconds": hybrid_metrics["latency_seconds"]["mean"] - natural_latency,
            "mean_latency_ratio": hybrid_metrics["latency_seconds"]["mean"] / natural_latency if natural_latency else None,
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
