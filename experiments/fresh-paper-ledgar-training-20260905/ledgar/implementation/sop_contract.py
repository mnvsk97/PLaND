#!/usr/bin/env python3
"""Validate and freeze PLaND SOP step/fallback relationships."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


STEP = re.compile(
    r"^\s*\d+[.)]\s+\[(S\d+)\]\s+(.+?)\s+"
    r"<!--\s*pland:(english|reference|command)(?:\s+fallback=(S\d+))?\s*-->\s*$",
    re.MULTILINE,
)
FALLBACK = re.compile(
    r"^\s*Fallback\s+\[(S\d+)\]:\s+(.+?)\s+<!--\s*pland:fallback\s*-->\s*$",
    re.MULTILINE,
)


def text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def parse_sop(content: str) -> dict[str, Any]:
    steps: dict[str, dict[str, str | None]] = {}
    for match in STEP.finditer(content):
        step_id, instruction, representation, fallback_id = match.groups()
        if step_id in steps:
            raise ValueError(f"duplicate SOP step ID: {step_id}")
        steps[step_id] = {
            "instruction": instruction,
            "instruction_sha256": text_sha256(instruction),
            "representation": representation,
            "fallback_step_id": fallback_id,
        }
    if not steps:
        raise ValueError("SOP contains no marked, stable-ID steps")
    fallbacks: dict[str, dict[str, str]] = {}
    for match in FALLBACK.finditer(content):
        step_id, instruction = match.groups()
        if step_id in fallbacks:
            raise ValueError(f"duplicate fallback for step: {step_id}")
        fallbacks[step_id] = {
            "instruction": instruction,
            "instruction_sha256": text_sha256(instruction),
        }
    return {"steps": steps, "fallbacks": fallbacks}


def baseline_contract(content: str) -> dict[str, Any]:
    parsed = parse_sop(content)
    invalid = [
        step_id for step_id, step in parsed["steps"].items()
        if step["representation"] != "english" or step["fallback_step_id"] is not None
    ]
    if invalid or parsed["fallbacks"]:
        raise ValueError("baseline SOP must contain only direct English steps and no fallback blocks")
    contract = {
        "schema_version": 1,
        "baseline_sop_sha256": text_sha256(content),
        "baseline_sop_content": content,
        "steps": {
            step_id: {
                "instruction": step["instruction"],
                "instruction_sha256": step["instruction_sha256"],
            }
            for step_id, step in parsed["steps"].items()
        },
    }
    contract["contract_sha256"] = canonical_sha256(contract)
    return contract


def validate_candidate(content: str, baseline: dict[str, Any]) -> dict[str, Any]:
    parsed = parse_sop(content)
    expected_ids = set(baseline["steps"])
    actual_ids = set(parsed["steps"])
    if actual_ids != expected_ids:
        missing = sorted(expected_ids - actual_ids)
        extra = sorted(actual_ids - expected_ids)
        raise ValueError(f"candidate step IDs differ from baseline; missing={missing}, extra={extra}")

    links = []
    for step_id, step in parsed["steps"].items():
        fallback_id = step["fallback_step_id"]
        if step["representation"] == "command":
            if fallback_id != step_id:
                raise ValueError(f"command step {step_id} must declare fallback={step_id}")
            fallback = parsed["fallbacks"].get(step_id)
            if fallback is None:
                raise ValueError(f"command step {step_id} has no explicit fallback block")
            original = baseline["steps"][step_id]
            if fallback["instruction"] != original["instruction"]:
                raise ValueError(f"fallback for {step_id} is not the exact baseline instruction")
            links.append({
                "command_step_id": step_id,
                "fallback_step_id": step_id,
                "fallback_instruction": fallback["instruction"],
                "fallback_instruction_sha256": fallback["instruction_sha256"],
            })
        elif fallback_id is not None:
            raise ValueError(f"non-command step {step_id} cannot declare a fallback link")

    unused = sorted(set(parsed["fallbacks"]) - {link["command_step_id"] for link in links})
    if unused:
        raise ValueError(f"fallback blocks are not linked from command steps: {unused}")
    if not links:
        raise ValueError("candidate is not hybrid: no command/fallback links")
    if not any(step["representation"] != "command" for step in parsed["steps"].values()):
        raise ValueError("candidate is not hybrid: no non-command steps")
    return {
        "valid": True,
        "baseline_contract_sha256": baseline["contract_sha256"],
        "baseline_sop_sha256": baseline["baseline_sop_sha256"],
        "candidate_sop_sha256": text_sha256(content),
        "command_fallback_links": links,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-sop", required=True, type=Path)
    parser.add_argument("--candidate-sop", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    baseline = baseline_contract(args.baseline_sop.read_text(encoding="utf-8"))
    result = (
        validate_candidate(args.candidate_sop.read_text(encoding="utf-8"), baseline)
        if args.candidate_sop else baseline
    )
    if args.output.exists():
        raise SystemExit(f"output already exists: {args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "valid", "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
