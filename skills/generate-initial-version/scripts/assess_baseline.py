#!/usr/bin/env python3
"""Decide whether an English baseline is ready to freeze using development only."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--attempt", required=True, type=int)
    parser.add_argument("--max-attempts", type=int, default=10)
    parser.add_argument("--minimum-quality", type=float, default=0.8)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"output already exists: {args.output}")
    if not 1 <= args.attempt <= args.max_attempts:
        raise SystemExit("--attempt must be within --max-attempts")
    if not 0 <= args.minimum_quality <= 1:
        raise SystemExit("--minimum-quality must be between 0 and 1")
    run = json.loads(args.run.read_text(encoding="utf-8"))
    if run.get("split") != "development":
        raise SystemExit("baseline readiness uses development only")
    if run.get("candidate_id") not in (None, "baseline"):
        raise SystemExit("baseline readiness cannot assess a hybrid candidate")
    summary = run.get("summary", {})
    quality = summary.get("quality", summary.get("accuracy"))
    if quality is None:
        raise SystemExit("run summary has no quality value")
    viable = (
        float(quality) >= args.minimum_quality
        and summary.get("normal_completion_rate", 1.0) > 0
        and not summary.get("errors")
    )
    decision = (
        "ready_to_freeze" if viable
        else "baseline_nonviable" if args.attempt == args.max_attempts
        else "refine_baseline"
    )
    result = {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "attempt": args.attempt,
        "max_attempts": args.max_attempts,
        "minimum_quality": args.minimum_quality,
        "observed_quality": quality,
        "run": str(args.run),
        "sop_sha256": run.get("sop_sha256") or run.get("sop", {}).get("sha256"),
        "decision": decision,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": decision, "attempt": args.attempt}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
