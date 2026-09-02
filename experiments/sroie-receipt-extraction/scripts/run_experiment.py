#!/usr/bin/env python3
"""Run the frozen SROIE natural-language versus hybrid SOP comparison."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import re
import resource
import shutil
import statistics
import subprocess
import time
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ("company", "date", "address", "total")
STEP = re.compile(r"^\s*\d+[.)].*pland:(english|reference|command)", re.M)


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def normalize(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def field_f1(expected: dict[str, str], actual: dict[str, str]) -> float:
    scores = []
    for field in FIELDS:
        gold = Counter(re.findall(r"[a-z0-9]+", expected[field].lower()))
        predicted = Counter(re.findall(r"[a-z0-9]+", actual.get(field, "").lower()))
        overlap = sum((gold & predicted).values())
        precision = overlap / sum(predicted.values()) if predicted else 0.0
        recall = overlap / sum(gold.values()) if gold else 0.0
        scores.append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)
    return statistics.fmean(scores)


def word_error_rate(reference: list[str], hypothesis: list[str]) -> float:
    ref = [normalize(word) for word in reference if normalize(word)]
    hyp = [normalize(word) for word in hypothesis if normalize(word)]
    previous = list(range(len(hyp) + 1))
    for index, source in enumerate(ref, 1):
        current = [index]
        for target_index, target in enumerate(hyp, 1):
            current.append(min(current[-1] + 1, previous[target_index] + 1,
                               previous[target_index - 1] + (source != target)))
        previous = current
    return previous[-1] / len(ref) if ref else float(bool(hyp))


def model_digest(model: str) -> str:
    with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=5) as response:
        payload = json.load(response)
    for item in payload.get("models", []):
        if item.get("name") == model or item.get("model") == model:
            return str(item["digest"])
    raise RuntimeError(f"local Ollama model is unavailable: {model}")


def sop_snapshot(path: Path) -> dict[str, Any]:
    content = path.read_text(encoding="utf-8")
    counts = Counter(STEP.findall(content))
    return {
        "path": str(path.relative_to(ROOT)), "sha256": digest_file(path), "content": content,
        "step_representations": {"total": sum(counts.values()), **{key: counts[key] for key in ("english", "reference", "command")}},
        "variant": "hybrid" if counts["command"] else "natural_language",
    }


def select_rows(dataset: Path, cases: int) -> list[dict[str, str]]:
    with (dataset / "evals.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    desired = {"development": round(cases * .6), "validation": round(cases * .2)}
    desired["test"] = cases - desired["development"] - desired["validation"]
    chosen = []
    for split, count in desired.items():
        available = sorted((row for row in rows if row["split"] == split), key=lambda row: row["id"])
        chosen.extend(available[:count])
    if len(chosen) != cases:
        raise RuntimeError(f"could not select {cases} cases")
    return chosen


def tesseract_words(image: Path) -> tuple[list[str], float, str]:
    started = time.perf_counter()
    command = ["tesseract", str(image), "stdout", "--oem", "1", "--psm", "6", "tsv"]
    result = subprocess.run(command, check=True, text=True, capture_output=True)
    elapsed = time.perf_counter() - started
    lines = list(csv.DictReader(result.stdout.splitlines(), delimiter="\t"))
    words = [line["text"].strip() for line in lines if line.get("text", "").strip()]
    return words, elapsed, result.stderr


def hybrid_candidates(words: list[str]) -> tuple[dict[str, Any], float]:
    temporary = ROOT / ".candidate-input.json"
    try:
        temporary.write_text(json.dumps({"words": words}), encoding="utf-8")
        started = time.perf_counter()
        result = subprocess.run([
            "python", str(ROOT / "hybrid/scripts/extract_candidates.py"), "--input", str(temporary)
        ], check=True, text=True, capture_output=True)
        elapsed = time.perf_counter() - started
        return json.loads(result.stdout), elapsed
    finally:
        temporary.unlink(missing_ok=True)


def invoke(model: str, system: str, prompt: str, seed: int) -> tuple[dict[str, str], dict[str, Any], float]:
    schema = {"type": "object", "properties": {field: {"type": "string"} for field in FIELDS},
              "required": list(FIELDS), "additionalProperties": False}
    body = json.dumps({
        "model": model, "stream": False, "think": False, "format": schema, "system": system,
        "prompt": prompt, "keep_alive": "30m",
        "options": {"seed": seed, "temperature": 0, "num_predict": 160},
    }).encode()
    request = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=body,
                                     headers={"Content-Type": "application/json"})
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=300) as response:
        raw = json.load(response)
    elapsed = time.perf_counter() - started
    parsed = json.loads(raw["response"])
    return {field: str(parsed.get(field, "")) for field in FIELDS}, raw, elapsed


def aggregate(cases: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = [case["total_latency_seconds"] for case in cases]
    return {
        "cases": len(cases),
        "field_f1": statistics.fmean(case["field_f1"] for case in cases),
        "document_exact_match": statistics.fmean(case["exact_match"] for case in cases),
        "field_exact_match": statistics.fmean(case["field_exact_match"] for case in cases),
        "input_tokens": sum(case["input_tokens"] for case in cases),
        "output_tokens": sum(case["output_tokens"] for case in cases),
        "total_tokens": sum(case["total_tokens"] for case in cases),
        "estimated_model_cost_usd": 0.0,
        "latency_seconds": {"total": sum(latencies), "mean": statistics.fmean(latencies)},
        "ocr_latency_seconds": sum(case["ocr_latency_seconds"] for case in cases),
        "agent_latency_seconds": sum(case["agent_latency_seconds"] for case in cases),
        "sop_code_latency_seconds": sum(case["sop_code_latency_seconds"] for case in cases),
        "ocr_word_error_rate": statistics.fmean(case["ocr_word_error_rate"] for case in cases),
        "peak_process_rss_bytes": max(case["process_max_rss_bytes"] for case in cases),
    }


def run_variant(dataset: Path, rows: list[dict[str, str]], variant: str, mode: str,
                config: dict[str, Any], invariants: dict[str, Any]) -> dict[str, Any]:
    sop = sop_snapshot(ROOT / variant / "SKILL.md")
    system = (ROOT / "system-prompt.md").read_text(encoding="utf-8")
    cases = []
    for index, row in enumerate(rows, 1):
        case = json.loads((dataset / row["input"]).read_text(encoding="utf-8"))
        frozen_words = [str(word) for word in case["frozen_ocr"]["words"]]
        ocr_latency, ocr_stderr = 0.0, ""
        if mode == "end-to-end":
            words, ocr_latency, ocr_stderr = tesseract_words(dataset / case["image"])
        else:
            words = frozen_words
        code_latency = 0.0
        if variant == "hybrid":
            evidence, code_latency = hybrid_candidates(words)
            evidence_text = json.dumps(evidence, ensure_ascii=False, separators=(",", ":"))
        else:
            evidence_text = json.dumps({"words": words}, ensure_ascii=False, separators=(",", ":"))
        prompt = f"Workflow SOP:\n{sop['content']}\n\nReceipt evidence:\n{evidence_text}"
        error = None
        started = time.perf_counter()
        try:
            actual, raw, agent_latency = invoke(config["model"], system, prompt, config["seed"])
        except Exception as exception:
            actual = {field: "" for field in FIELDS}
            raw, agent_latency = {}, time.perf_counter() - started
            error = f"{type(exception).__name__}: {exception}"
        expected = json.loads(row["output"])
        exact_fields = [normalize(actual[field]) == normalize(expected[field]) for field in FIELDS]
        max_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if platform.system() != "Darwin":
            max_rss *= 1024
        case_result = {
            "id": row["id"], "split": row["split"], "expected": expected, "actual": actual,
            "field_f1": field_f1(expected, actual), "field_exact_match": statistics.fmean(exact_fields),
            "exact_match": int(all(exact_fields)), "error": error,
            "input_tokens": int(raw.get("prompt_eval_count", 0)), "output_tokens": int(raw.get("eval_count", 0)),
            "total_tokens": int(raw.get("prompt_eval_count", 0)) + int(raw.get("eval_count", 0)),
            "ocr_latency_seconds": ocr_latency, "sop_code_latency_seconds": code_latency,
            "agent_latency_seconds": agent_latency,
            "total_latency_seconds": ocr_latency + code_latency + agent_latency,
            "ocr_word_error_rate": word_error_rate(frozen_words, words),
            "process_max_rss_bytes": max_rss, "ocr_stderr": ocr_stderr,
            "trace": {"prompt": prompt, "raw_response": raw},
        }
        cases.append(case_result)
        print(f"{mode} {variant} {index}/{len(rows)} {row['id']} f1={case_result['field_f1']:.3f}", flush=True)
    return {"schema_version": 2, "variant": variant, "mode": mode, "sop": sop,
            "invariants": invariants, "metrics": aggregate(cases), "cases": cases}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if not shutil.which("tesseract"):
        raise SystemExit("tesseract is required")
    config = json.loads((ROOT / "experiment.json").read_text(encoding="utf-8"))
    rows = select_rows(args.dataset, config["cases"])
    selection = json.loads((args.dataset / "selection.json").read_text(encoding="utf-8"))
    selected_manifest = [{"id": row["id"], "split": row["split"], "input_sha256": digest_file(args.dataset / row["input"]),
                          "output_sha256": digest_bytes(row["output"].encode())} for row in rows]
    invariants = {
        "model": config["model"], "model_digest": model_digest(config["model"]), "seed": config["seed"],
        "system_prompt_sha256": digest_file(ROOT / "system-prompt.md"),
        "harness_sha256": digest_file(Path(__file__)), "scorer_sha256": digest_file(Path(__file__)),
        "dataset_selection_sha256": digest_file(args.dataset / "selection.json"),
        "datasource_snapshot_sha256": selection["sources"][0]["sha256"],
        "selected_cases_sha256": digest_bytes(json.dumps(selected_manifest, sort_keys=True).encode()),
        "execution_permissions": config["execution_permissions"],
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "selected-cases.json").write_text(json.dumps(selected_manifest, indent=2) + "\n")
    all_runs: dict[str, Any] = {}
    for mode in ("frozen-ocr", "end-to-end"):
        for variant in ("nl-baseline", "hybrid"):
            key = f"{mode}-{variant}"
            result_path = args.output / f"{key}.json"
            if result_path.exists():
                result = json.loads(result_path.read_text(encoding="utf-8"))
                if result.get("invariants") != invariants:
                    raise RuntimeError(f"refusing to resume {key}: frozen invariants changed")
                print(f"resumed {key}", flush=True)
            else:
                result = run_variant(args.dataset, rows, variant, mode, config, invariants)
            all_runs[key] = result
            result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    comparisons = {}
    for mode in ("frozen-ocr", "end-to-end"):
        baseline = all_runs[f"{mode}-nl-baseline"]
        candidate = all_runs[f"{mode}-hybrid"]
        base_val = aggregate([case for case in baseline["cases"] if case["split"] == "validation"])
        cand_val = aggregate([case for case in candidate["cases"] if case["split"] == "validation"])
        accepted = cand_val["field_f1"] >= base_val["field_f1"] and cand_val["total_tokens"] < base_val["total_tokens"]
        comparisons[mode] = {
            "baseline": baseline["metrics"], "candidate": candidate["metrics"],
            "validation_baseline": base_val, "validation_candidate": cand_val,
            "accepted": accepted,
            "decision": "accept" if accepted else "reject",
            "reason": "validation quality floor preserved and token objective improved" if accepted else "quality floor or token objective failed",
            "iteration": 1, "max_iterations": config["max_iterations"],
        }
    (args.output / "comparison.json").write_text(json.dumps({"invariants": invariants, "modes": comparisons}, indent=2) + "\n")
    print(json.dumps({mode: value["decision"] for mode, value in comparisons.items()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
