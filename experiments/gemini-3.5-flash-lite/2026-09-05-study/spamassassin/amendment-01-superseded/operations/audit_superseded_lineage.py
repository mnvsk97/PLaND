#!/usr/bin/env python3
"""Audit a preserved, superseded amendment lineage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"output exists: {args.output}")
    state = json.loads((args.run_dir / "collection-state.json").read_text(encoding="utf-8"))
    dataset = json.loads((args.run_dir / "results/dataset-amendment-audit.json").read_text(encoding="utf-8"))
    carry = json.loads((args.run_dir / "results/development-carry-forward-audit.json").read_text(encoding="utf-8"))
    selection = json.loads((args.run_dir / "results/selection-superseded-assessment.json").read_text(encoding="utf-8"))
    decisions = {key: (values[-1]["value"] if values else None)
                 for key, values in state["decisions"].items()}
    checks = {"dataset_audit": dataset.get("passed") is True,
              "development_carry_forward": carry.get("passed") is True,
              "baseline_ready": decisions.get("baseline-development") == "ready",
              "candidate_ready": decisions.get("candidate-development") == "ready",
              "selection_rejected": decisions.get("selection") == "reject",
              "superseded_disposition": selection.get("disposition") == "superseded_by_amendment_02",
              "final_test_unopened": state["stages"].get("final-test") == "pending"
                  and not list((args.run_dir / "results").glob("final-test-repeat-*.json"))}
    result = {"schema_version": 1, "outcome": "superseded_by_amendment_02",
              "decisions": decisions, "checks": checks, "passed": all(checks.values())}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
