#!/usr/bin/env python3
"""Require every frozen selection repeat to pass before final-test release."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--comparison", action="append", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"output exists: {args.output}")
    comparisons = []
    for path in args.comparison:
        value = json.loads(path.read_text(encoding="utf-8"))
        comparisons.append({"path": str(path), "gate": value.get("gate"),
                            "accuracy_difference_bootstrap_95": value["paired_statistics"]["accuracy_difference_bootstrap_95"],
                            "token_reduction_bootstrap_95": value["paired_statistics"]["token_reduction_bootstrap_95"]})
    accepted = len(comparisons) == 3 and all(item["gate"].get("test_release_pass") is True
                                              for item in comparisons)
    result = {"schema_version": 1, "stage": "selection", "candidate": "candidate-02",
              "comparisons": comparisons, "decision": "accept" if accepted else "reject",
              "final_test_released": accepted}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "comparisons": len(comparisons)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
