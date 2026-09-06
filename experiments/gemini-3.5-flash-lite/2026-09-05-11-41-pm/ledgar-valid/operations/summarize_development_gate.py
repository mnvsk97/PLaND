#!/usr/bin/env python3
"""Require the primary and all three development repeat assessments to pass."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assessment", action="append", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"output exists: {args.output}")
    assessments = []
    for path in args.assessment:
        value = json.loads(path.read_text(encoding="utf-8"))
        assessments.append({"path": str(path), "decision": value.get("decision"),
                            "failed_checks": value.get("failed_checks", [])})
    ready = all(item["decision"] == "eligible_for_validation" and not item["failed_checks"]
                for item in assessments)
    result = {"schema_version": 1, "stage": "candidate-development", "candidate": "candidate-02",
              "assessments": assessments, "decision": "ready" if ready else "refine"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "assessments": len(assessments)}))
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
