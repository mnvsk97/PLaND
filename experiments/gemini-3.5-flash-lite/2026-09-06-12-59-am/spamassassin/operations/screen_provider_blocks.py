#!/usr/bin/env python3
"""Screen remaining opened selection cases for provider content blocks."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[5]
load_dotenv(ROOT / ".env", override=False)
WRITE_LOCK = threading.Lock()


def atomic_write(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def retry_delay(attempt: int, case_id: str, headers) -> float:
    raw = headers.get("retry-after-ms")
    try:
        value = float(raw) / 1000 if raw is not None else None
    except (TypeError, ValueError):
        value = None
    if value is None:
        raw = headers.get("retry-after")
        try:
            value = float(raw) if raw is not None else None
        except (TypeError, ValueError):
            value = None
    if value is None or not math.isfinite(value) or value <= 0:
        jitter = 0.75 + int(hashlib.sha256(case_id.encode()).hexdigest()[:2], 16) / 510
        value = min(60.0, 2.0 ** min(attempt, 6)) * jitter
    return min(300.0, max(0.1, value))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--existing-partial", required=True, type=Path)
    parser.add_argument("--system-prompt", required=True, type=Path)
    parser.add_argument("--sop", required=True, type=Path)
    parser.add_argument("--workers", type=int, required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"output exists: {args.output}")
    with (args.dataset / "evals.csv").open(encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["split"] == "validation"]
    completed = {case["id"] for case in json.loads(args.existing_partial.read_text(encoding="utf-8"))["cases"]}
    labels = sorted({json.loads(row["output"])["label"] for row in rows})
    system = args.system_prompt.read_text(encoding="utf-8")
    sop = args.sop.read_text(encoding="utf-8")
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["MODEL_API_KEY"], base_url=os.environ["MODEL_BASE_URL"],
                    timeout=300, max_retries=0)
    schema = {"type": "object", "properties": {"label": {"type": "string", "enum": labels}},
              "required": ["label"], "additionalProperties": False}

    def screen(row: dict[str, str]) -> dict:
        payload = json.loads((args.dataset / row["input"]).read_text(encoding="utf-8"))
        prompt = (f"Workflow SOP:\n{sop}\n\nAllowed labels:\n{json.dumps(labels)}\n\n"
                  f"Classify this document:\n{payload['raw_email']}\n\nReturn exactly one JSON object with label.")
        attempt = 0
        while True:
            attempt += 1
            try:
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
                code = error.get("code") if isinstance(error, dict) else None
                message = error.get("message", "") if isinstance(error, dict) else ""
                if code == 429:
                    time.sleep(retry_delay(attempt, row["id"], response.http_response.headers))
                    continue
                if isinstance(body.get("choices"), list) and body["choices"]:
                    return {"id": row["id"], "status": "pass", "attempts": attempt}
                if code == 400 and message == "Gemini blocked the request: PROHIBITED_CONTENT":
                    return {"id": row["id"], "status": "prohibited_content", "attempts": attempt,
                            "error_code": code, "message_sha256": hashlib.sha256(message.encode()).hexdigest()}
                return {"id": row["id"], "status": "other_terminal_error", "attempts": attempt,
                        "error_code": code, "message_sha256": hashlib.sha256(str(message).encode()).hexdigest()}
            except Exception as error:
                status = getattr(error, "status_code", None)
                response = getattr(error, "response", None)
                if status == 429 or getattr(response, "status_code", None) == 429:
                    time.sleep(retry_delay(attempt, row["id"], getattr(response, "headers", {})))
                    continue
                if attempt < 5:
                    time.sleep(min(10.0, 0.5 * 2 ** attempt + random.random()))
                    continue
                return {"id": row["id"], "status": "transport_error", "attempts": attempt,
                        "error_type": type(error).__name__}

    pending = [row for row in rows if row["id"] not in completed]
    outcomes = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        iterator = iter(pending)
        futures = set()
        while len(futures) < args.workers:
            row = next(iterator, None)
            if row is None:
                break
            futures.add(executor.submit(screen, row))
        while futures:
            done, _ = wait(futures, return_when=FIRST_COMPLETED)
            for future in done:
                futures.remove(future)
                outcomes.append(future.result())
                row = next(iterator, None)
                if row is not None:
                    futures.add(executor.submit(screen, row))
    blocked = sorted(item["id"] for item in outcomes if item["status"] == "prohibited_content")
    other = [item for item in outcomes if item["status"] not in {"pass", "prohibited_content"}]
    result = {"schema_version": 1, "split": "validation", "cases": len(rows),
              "previously_completed": len(completed), "screened": len(outcomes),
              "workers": args.workers, "blocked_case_ids": blocked,
              "blocked_count": len(blocked), "other_terminal_errors": other,
              "rate_limits_retried_not_failed": True,
              "passed": not other}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(args.output, result)
    print(json.dumps({key: result[key] for key in ("cases", "previously_completed", "screened",
                                                    "blocked_count", "other_terminal_errors", "passed")}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
