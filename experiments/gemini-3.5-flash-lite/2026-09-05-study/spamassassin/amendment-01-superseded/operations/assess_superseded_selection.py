#!/usr/bin/env python3
"""Assess a selection lineage superseded by an additional blocked case."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--partial", required=True, type=Path)
    parser.add_argument("--attempts", required=True, type=Path)
    parser.add_argument("--screen", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"output exists: {args.output}")
    partial = json.loads(args.partial.read_text(encoding="utf-8"))
    screen = json.loads(args.screen.read_text(encoding="utf-8"))
    failures = []
    for path in args.attempts.glob("*.json"):
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("status") == "failed":
            failures.append(value)
    blocked = screen.get("blocked_case_ids", [])
    checks = {
        "partial_preserved": len(partial.get("cases", [])) == screen.get("previously_completed"),
        "one_failed_receipt": len(failures) == 1,
        "one_additional_block": len(blocked) == 1,
        "failed_case_is_blocked_case": bool(failures) and failures[0].get("case_id") == blocked[0],
        "remaining_cases_screened": screen.get("screened") + screen.get("previously_completed") == 1000,
        "no_other_terminal_errors": not screen.get("other_terminal_errors"),
        "rate_limits_not_failed": screen.get("rate_limits_retried_not_failed") is True,
    }
    if not all(checks.values()):
        raise SystemExit("superseded selection evidence is inconsistent")
    result = {"schema_version": 1, "stage": "selection", "candidate": "candidate-01",
              "decision": "reject", "disposition": "superseded_by_amendment_02",
              "additional_blocked_case_ids": blocked,
              "completed_cases_before_block": len(partial["cases"]),
              "checks": checks, "final_test_release": False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
