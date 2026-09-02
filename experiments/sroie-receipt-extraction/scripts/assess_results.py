#!/usr/bin/env python3
"""Apply the preregistered quality and expense gates to completed runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def decision(baseline: dict, candidate: dict, minimum: float) -> dict:
    viable = baseline["field_f1"] >= minimum
    quality_preserved = candidate["field_f1"] >= baseline["field_f1"]
    expense_improved = candidate["total_tokens"] < baseline["total_tokens"]
    accepted = viable and quality_preserved and expense_improved
    return {
        "accepted": accepted,
        "baseline_viable": viable,
        "quality_preserved": quality_preserved,
        "expense_improved": expense_improved,
        "reason": (
            "accepted"
            if accepted else
            "baseline below minimum viable quality; optimization result is not meaningful"
            if not viable else
            "candidate did not preserve the validation quality floor"
            if not quality_preserved else
            "candidate did not improve the token objective"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / "experiment.json").read_text())
    comparison = json.loads((args.results / "comparison.json").read_text())
    output = {"minimum_viable_baseline_field_f1": config["minimum_viable_baseline_field_f1"], "modes": {}}
    for mode, values in comparison["modes"].items():
        output["modes"][mode] = decision(values["validation_baseline"], values["validation_candidate"],
                                         config["minimum_viable_baseline_field_f1"])
    (args.results / "assessment.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
