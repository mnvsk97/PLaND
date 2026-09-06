#!/usr/bin/env python3
"""Capture only the non-sensitive shape and status of one raw hosted response."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[5]
load_dotenv(ROOT / ".env", override=False)


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
    labels = sorted({json.loads(item["output"])["label"] for item in rows})
    system = args.system_prompt.read_text(encoding="utf-8")
    sop = args.sop.read_text(encoding="utf-8")
    prompt = (f"Workflow SOP:\n{sop}\n\nAllowed labels:\n{json.dumps(labels)}\n\n"
              f"Classify this document:\n{payload['raw_email']}\n\nReturn exactly one JSON object with label.")
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["MODEL_API_KEY"],
                    base_url=os.environ["MODEL_BASE_URL"], timeout=300, max_retries=0)
    schema = {"type": "object", "properties": {"label": {"type": "string", "enum": labels}},
              "required": ["label"], "additionalProperties": False}
    response = client.chat.completions.with_raw_response.create(
        model=os.environ["MODEL_NAME"],
        messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        max_tokens=1024,
        response_format={"type": "json_schema", "json_schema": {
            "name": "classification", "strict": True, "schema": schema}},
        extra_body=json.loads(os.environ.get("MODEL_EXTRA_BODY_JSON", "{}")),
    )
    body = response.http_response.json()
    error = body.get("error") if isinstance(body, dict) else None
    message = error.get("message", "") if isinstance(error, dict) else ""
    message_folded = message.casefold() if isinstance(message, str) else ""
    safe_message = None
    if (isinstance(message, str) and len(message) <= 200 and "@" not in message
            and "sk-" not in message.casefold() and "{" not in message and "}" not in message):
        safe_message = message
    result = {
        "schema_version": 1,
        "case_id": args.case_id,
        "sensitive_content_recorded": False,
        "http_status": response.http_response.status_code,
        "top_level_keys": sorted(body) if isinstance(body, dict) else None,
        "choices_type": type(body.get("choices")).__name__ if isinstance(body, dict) else None,
        "choices_count": len(body["choices"]) if isinstance(body, dict) and isinstance(body.get("choices"), list) else None,
        "error_type": error.get("type") if isinstance(error, dict) else None,
        "error_code": error.get("code") if isinstance(error, dict) else None,
        "error_keys": sorted(error) if isinstance(error, dict) else None,
        "message_length": len(message) if isinstance(message, str) else None,
        "message_sha256": hashlib.sha256(message.encode()).hexdigest() if isinstance(message, str) else None,
        "safe_message": safe_message,
        "message_categories": {
            key: key in message_folded
            for key in ("rate limit", "context", "token", "input", "invalid", "safety", "provider")
        },
        "retry_after": response.http_response.headers.get("retry-after"),
        "retry_after_ms": response.http_response.headers.get("retry-after-ms"),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
