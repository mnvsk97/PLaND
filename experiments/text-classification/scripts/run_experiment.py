#!/usr/bin/env python3
"""Run a frozen text-classification SOP against a prepared PLaND eval set."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import re
import resource
import statistics
import time
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


STEP = re.compile(r"^\s*\d+[.)].*?pland:(english|reference|command)", re.MULTILINE)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ollama(
    model: str,
    system: str,
    prompt: str,
    seed: int,
    labels: list[str],
    num_ctx: int,
    num_predict: int,
    keep_alive: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    schema = {
        "type": "object",
        "properties": {
            "label": {"type": "string", "enum": labels},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["label", "confidence"],
        "additionalProperties": False,
    }
    body = json.dumps({
        "model": model,
        "stream": False,
        "think": False,
        "keep_alive": keep_alive,
        "format": schema,
        "options": {
            "temperature": 0,
            "seed": seed,
            "num_ctx": num_ctx,
            "num_predict": num_predict,
        },
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
    }).encode()
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat", data=body,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        raw = json.load(response)
    try:
        prediction = json.loads(raw["message"]["content"])
    except (KeyError, json.JSONDecodeError, TypeError):
        prediction = {}
    return prediction, raw


def runtime_contract(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "think": False,
        "stream": False,
        "temperature": 0,
        "num_ctx": args.num_ctx,
        "num_predict": args.num_predict,
        "keep_alive": args.keep_alive,
        "workers": args.workers,
        "ollama_flash_attention": os.environ.get("OLLAMA_FLASH_ATTENTION"),
        "ollama_kv_cache_type": os.environ.get("OLLAMA_KV_CACHE_TYPE"),
        "ollama_num_parallel": os.environ.get("OLLAMA_NUM_PARALLEL"),
        "ollama_max_loaded_models": os.environ.get("OLLAMA_MAX_LOADED_MODELS"),
    }


def model_digest(model: str) -> str | None:
    with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=10) as response:
        payload = json.load(response)
    for item in payload.get("models", []):
        if item.get("name") == model or item.get("model") == model:
            return item.get("digest")
    return None


def load_classifier(path: Path | None):
    if path is None:
        return None
    spec = importlib.util.spec_from_file_location("pland_classifier", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load classifier: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.classify


def macro_f1(cases: list[dict[str, Any]], labels: list[str]) -> float:
    scores = []
    for label in labels:
        tp = sum(c["expected"] == label and c["actual"] == label for c in cases)
        fp = sum(c["expected"] != label and c["actual"] == label for c in cases)
        fn = sum(c["expected"] == label and c["actual"] != label for c in cases)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        scores.append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)
    return statistics.fmean(scores)


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--split", required=True, choices=("development", "validation", "test"))
    parser.add_argument("--system-prompt", required=True, type=Path)
    parser.add_argument("--sop", required=True, type=Path)
    parser.add_argument("--classifier", type=Path)
    parser.add_argument("--model", default="qwen3:14b")
    parser.add_argument("--seed", type=int, default=20260902)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--resume", action="store_true",
                        help="Resume from OUTPUT.partial.json when present")
    parser.add_argument("--checkpoint-every", type=int, default=10)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--num-ctx", type=int, default=4096)
    parser.add_argument("--num-predict", type=int, default=128)
    parser.add_argument("--keep-alive", type=int, default=-1)
    parser.add_argument("--limit", type=int,
                        help="Run only the first N selected cases for a smoke test")
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"output exists: {args.output}")
    if args.checkpoint_every < 1:
        raise SystemExit("--checkpoint-every must be positive")
    if args.workers < 1 or args.num_ctx < 1 or args.num_predict < 1:
        raise SystemExit("--workers, --num-ctx, and --num-predict must be positive")

    with (args.dataset / "evals.csv").open(encoding="utf-8", newline="") as handle:
        all_rows = list(csv.DictReader(handle))
    rows = [row for row in all_rows if row["split"] == args.split]
    if args.limit is not None:
        if args.limit < 1:
            raise SystemExit("--limit must be positive")
        rows = rows[:args.limit]
    labels = sorted({json.loads(row["output"])["label"] for row in all_rows})
    system = args.system_prompt.read_text(encoding="utf-8")
    sop = args.sop.read_text(encoding="utf-8")
    classifier = load_classifier(args.classifier)
    partial_path = args.output.with_suffix(args.output.suffix + ".partial.json")
    cases: list[dict[str, Any]] = []
    if args.resume and partial_path.exists():
        partial = json.loads(partial_path.read_text(encoding="utf-8"))
        expected_resume = {
            "dataset": str(args.dataset.resolve()),
            "split": args.split,
            "model": args.model,
            "seed": args.seed,
            "system_prompt_sha256": digest(args.system_prompt),
            "sop_sha256": digest(args.sop),
            "evals_sha256": digest(args.dataset / "evals.csv"),
            "selection_sha256": digest(args.dataset / "selection.json"),
            "classifier_sha256": digest(args.classifier) if args.classifier else None,
            "runtime": runtime_contract(args),
        }
        if partial.get("resume_contract") != expected_resume:
            raise SystemExit("partial checkpoint does not match the requested run")
        cases = partial.get("cases", [])
    completed_ids = {case["id"] for case in cases}
    started_run = time.perf_counter()

    def run_case(row: dict[str, str]) -> dict[str, Any]:
        payload = json.loads((args.dataset / row["input"]).read_text(encoding="utf-8"))
        text = payload.get("text") or payload.get("narrative") or payload.get("raw_email")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"case {row['id']} has no supported text input")
        expected = json.loads(row["output"])["label"]
        started = time.perf_counter()
        source = "model"
        raw: dict[str, Any] = {}
        predicted = classifier(text, labels) if classifier else None
        if isinstance(predicted, dict) and predicted.get("label") in labels:
            actual = predicted["label"]
            confidence = predicted.get("confidence")
            source = "command"
            parse_error = None
        else:
            prompt = (
                f"Workflow SOP:\n{sop}\n\nAllowed labels:\n{json.dumps(labels)}\n\n"
                f"Classify this document:\n{text}\n\n"
                "Return exactly one JSON object with label and confidence."
            )
            value, raw = ollama(
                args.model, system, prompt, args.seed, labels,
                args.num_ctx, args.num_predict, args.keep_alive,
            )
            actual = value.get("label") if value.get("label") in labels else None
            confidence = value.get("confidence")
            parse_error = None if actual is not None and isinstance(confidence, (int, float)) else "invalid_prediction_schema"
        elapsed = time.perf_counter() - started
        return {
            "id": row["id"], "expected": expected, "actual": actual,
            "correct": actual == expected, "source": source, "confidence": confidence,
            "parse_error": parse_error,
            "raw_message_content": raw.get("message", {}).get("content"),
            "latency_seconds": elapsed,
            "input_tokens": raw.get("prompt_eval_count", 0),
            "output_tokens": raw.get("eval_count", 0),
            "total_tokens": raw.get("prompt_eval_count", 0) + raw.get("eval_count", 0),
            "ollama_load_ns": raw.get("load_duration", 0),
            "ollama_prompt_ns": raw.get("prompt_eval_duration", 0),
            "ollama_eval_ns": raw.get("eval_duration", 0),
        }

    pending_rows = [row for row in rows if row["id"] not in completed_ids]
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        for row, case in zip(pending_rows, executor.map(run_case, pending_rows), strict=True):
            cases.append(case)
            actual = case["actual"]
            expected = case["expected"]
            print(json.dumps({"id": row["id"], "correct": actual == expected, "source": case["source"]}))
            if len(cases) % args.checkpoint_every == 0:
                write_json_atomic(partial_path, {
                    "schema_version": 1,
                    "resume_contract": {
                        "dataset": str(args.dataset.resolve()),
                        "split": args.split,
                        "model": args.model,
                        "seed": args.seed,
                        "system_prompt_sha256": digest(args.system_prompt),
                        "sop_sha256": digest(args.sop),
                        "evals_sha256": digest(args.dataset / "evals.csv"),
                        "selection_sha256": digest(args.dataset / "selection.json"),
                        "classifier_sha256": digest(args.classifier) if args.classifier else None,
                        "runtime": runtime_contract(args),
                    },
                    "cases": cases,
                })

    latencies = [case["latency_seconds"] for case in cases]
    correct = sum(case["correct"] for case in cases)
    representations = Counter(STEP.findall(sop))
    payload = {
        "schema_version": 1, "created_at": datetime.now(UTC).isoformat(),
        "dataset": args.dataset.name, "split": args.split, "model": args.model,
        "model_digest": model_digest(args.model),
        "seed": args.seed,
        "runtime": runtime_contract(args),
        "invariants": {
            "system_prompt_sha256": digest(args.system_prompt),
            "evals_sha256": digest(args.dataset / "evals.csv"),
            "selection_sha256": digest(args.dataset / "selection.json"),
            "scorer_sha256": digest(Path(__file__)),
            "agent_harness_sha256": digest(Path(__file__)),
        },
        "sop": {
            "sha256": digest(args.sop),
            "classifier_sha256": digest(args.classifier) if args.classifier else None,
            "content": sop,
            "step_representations": dict(representations),
        },
        "summary": {
            "cases": len(cases), "correct": correct, "accuracy": correct / len(cases),
            "macro_f1": macro_f1(cases, labels),
            "input_tokens": sum(c["input_tokens"] for c in cases),
            "output_tokens": sum(c["output_tokens"] for c in cases),
            "total_tokens": sum(c["total_tokens"] for c in cases),
            "estimated_model_cost_usd": 0.0,
            "model_calls": sum(c["source"] == "model" for c in cases),
            "command_calls": sum(c["source"] == "command" for c in cases),
            "latency_seconds": {"total": sum(latencies), "mean": statistics.fmean(latencies)},
            "wall_seconds": time.perf_counter() - started_run,
            "max_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        },
        "cases": cases,
    }
    write_json_atomic(args.output, payload)
    partial_path.unlink(missing_ok=True)
    print(json.dumps(payload["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
