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
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


STEP = re.compile(r"^\s*\d+[.)].*?pland:(english|reference|command)", re.MULTILINE)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ollama(model: str, system: str, prompt: str, seed: int) -> tuple[dict[str, Any], dict[str, Any]]:
    body = json.dumps({
        "model": model,
        "stream": False,
        "think": False,
        "format": "json",
        "options": {"temperature": 0, "seed": seed, "num_predict": 128},
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
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"output exists: {args.output}")

    with (args.dataset / "evals.csv").open(encoding="utf-8", newline="") as handle:
        all_rows = list(csv.DictReader(handle))
    rows = [row for row in all_rows if row["split"] == args.split]
    labels = sorted({json.loads(row["output"])["label"] for row in all_rows})
    system = args.system_prompt.read_text(encoding="utf-8")
    sop = args.sop.read_text(encoding="utf-8")
    classifier = load_classifier(args.classifier)
    cases = []
    started_run = time.perf_counter()
    for row in rows:
        payload = json.loads((args.dataset / row["input"]).read_text(encoding="utf-8"))
        text = payload.get("text") or payload.get("narrative")
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
            value, raw = ollama(args.model, system, prompt, args.seed)
            actual = value.get("label") if value.get("label") in labels else None
            confidence = value.get("confidence")
            parse_error = None if actual is not None and isinstance(confidence, (int, float)) else "invalid_prediction_schema"
        elapsed = time.perf_counter() - started
        cases.append({
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
        })
        print(json.dumps({"id": row["id"], "correct": actual == expected, "source": source}))

    latencies = [case["latency_seconds"] for case in cases]
    correct = sum(case["correct"] for case in cases)
    representations = Counter(STEP.findall(sop))
    payload = {
        "schema_version": 1, "created_at": datetime.now(UTC).isoformat(),
        "dataset": args.dataset.name, "split": args.split, "model": args.model,
        "model_digest": model_digest(args.model),
        "seed": args.seed,
        "invariants": {
            "system_prompt_sha256": digest(args.system_prompt),
            "evals_sha256": digest(args.dataset / "evals.csv"),
            "selection_sha256": digest(args.dataset / "selection.json"),
            "scorer_sha256": digest(Path(__file__)),
            "agent_harness_sha256": digest(Path(__file__)),
        },
        "sop": {"sha256": digest(args.sop), "content": sop,
                "step_representations": dict(representations)},
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
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
