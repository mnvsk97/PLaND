#!/usr/bin/env python3
"""Diagnose one already-opened hosted case without recording sensitive text."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import traceback
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "experiments/collection/scripts"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--system-prompt", required=True, type=Path)
    parser.add_argument("--sop", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"output exists: {args.output}")
    with (args.dataset / "evals.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    row = next(item for item in rows if item["id"] == args.case_id)
    payload = json.loads((args.dataset / row["input"]).read_text(encoding="utf-8"))
    text = payload.get("raw_email")
    labels = sorted({json.loads(item["output"])["label"] for item in rows})
    system = args.system_prompt.read_text(encoding="utf-8")
    sop = args.sop.read_text(encoding="utf-8")
    prompt = (f"Workflow SOP:\n{sop}\n\nAllowed labels:\n{json.dumps(labels)}\n\n"
              f"Classify this document:\n{text}\n\nReturn exactly one JSON object with label.")
    result = {"schema_version": 1, "case_id": args.case_id, "sensitive_content_recorded": False}
    try:
        from deepagent_execution import invoke
        from hosted_execution import HostedConfig, MODEL
        value, raw = invoke(MODEL, system, prompt, labels, HostedConfig(1024, 300))
        result.update(status="completed", valid_label=value.get("label") in labels,
                      provider_receipts=len(raw.get("request_receipts", [])))
    except Exception as error:
        frames = traceback.extract_tb(error.__traceback__)
        result.update(status="failed", error_type=type(error).__name__,
                      frames=[{"file": Path(frame.filename).name, "line": frame.lineno,
                               "function": frame.name} for frame in frames])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
