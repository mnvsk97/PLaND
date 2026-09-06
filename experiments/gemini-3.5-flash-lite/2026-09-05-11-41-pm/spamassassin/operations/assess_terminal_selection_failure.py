#!/usr/bin/env python3
"""Record a deterministic selection rejection for a terminal provider block."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--partial", required=True, type=Path)
    parser.add_argument("--diagnostic", required=True, type=Path)
    parser.add_argument("--preserved-receipts", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"output exists: {args.output}")
    partial = json.loads(args.partial.read_text(encoding="utf-8"))
    diagnostic = json.loads(args.diagnostic.read_text(encoding="utf-8"))
    receipts = sorted(args.preserved_receipts.glob("attempt-*-failed-receipt.json"))
    preserved = [json.loads(path.read_text(encoding="utf-8")) for path in receipts]
    case_id = diagnostic.get("case_id")
    checks = {
        "selection_split": partial.get("resume_contract", {}).get("split") == "validation",
        "seed_20260903": partial.get("resume_contract", {}).get("seed") == 20260903,
        "baseline_arm": partial.get("resume_contract", {}).get("classifier_sha256") is None,
        "partial_cases_preserved": len(partial.get("cases", [])) > 0,
        "three_failed_attempts_preserved": len(receipts) == 3,
        "same_case_failed_each_attempt": bool(receipts) and all(item.get("case_id") == case_id for item in preserved),
        "not_rate_limited": diagnostic.get("retry_after") is None
            and diagnostic.get("retry_after_ms") is None
            and not diagnostic.get("message_categories", {}).get("rate limit"),
        "terminal_provider_block": diagnostic.get("http_status") == 200
            and diagnostic.get("error_code") == 400
            and diagnostic.get("safe_message") == "Gemini blocked the request: PROHIBITED_CONTENT",
    }
    if not all(checks.values()):
        raise SystemExit("terminal selection failure evidence is incomplete or inconsistent")
    result = {
        "schema_version": 1,
        "stage": "selection",
        "candidate": "candidate-01",
        "split": "validation",
        "seed": 20260903,
        "arm": "baseline",
        "case_id": case_id,
        "completed_cases_before_terminal_failure": len(partial["cases"]),
        "failed_attempts": len(receipts),
        "checks": checks,
        "gates": {
            "absolute_viability": "not_computable",
            "paired_noninferiority": "not_computable",
            "token_reduction": "not_computable",
            "paired_no_errors": False,
        },
        "decision": "reject",
        "final_test_release": False,
        "reason": "The frozen hosted provider terminally blocked one required selection case on three attempts; complete paired scoring and the no-errors release gate cannot pass without changing the reviewed runtime or data.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": "reject", "case_id": case_id,
                      "completed_cases": len(partial["cases"]), "failed_attempts": len(receipts)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
