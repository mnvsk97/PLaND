#!/usr/bin/env python3
"""Publish aggregate-only experiment evidence without private/raw case traces."""
import argparse, json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--runs", required=True, type=Path)
parser.add_argument("--output", required=True, type=Path)
args = parser.parse_args()
result = {"schema_version": 1,
          "note": "Aggregate metrics only; case traces remain in ignored local storage. Latency is concurrency-confounded and is not causal evidence.",
          "splits": {}}
all_cases = {"natural_language": [], "hybrid": []}
for split in ("development", "validation", "test"):
    nl = json.loads((args.runs / f"nl-{split}.json").read_text())
    hybrid = json.loads((args.runs / f"hybrid-{split}.json").read_text())
    comparison = json.loads((args.runs / f"comparison-{split}.json").read_text())
    result["splits"][split] = {
        "natural_language": nl["summary"], "hybrid": hybrid["summary"],
        "delta_hybrid_minus_nl": comparison["delta_hybrid_minus_nl"],
        "invariants": nl["invariants"], "model": nl["model"],
        "model_digest": nl["model_digest"], "seed": nl["seed"],
        "natural_language_sop": nl["sop"], "hybrid_sop": hybrid["sop"],
    }
    all_cases["natural_language"].extend(nl["cases"])
    all_cases["hybrid"].extend(hybrid["cases"])
result["overall"] = {}
for variant, cases in all_cases.items():
    labels = sorted({case["expected"] for case in cases})
    f1s = []
    for label in labels:
        tp = sum(c["expected"] == label and c["actual"] == label for c in cases)
        fp = sum(c["expected"] != label and c["actual"] == label for c in cases)
        fn = sum(c["expected"] == label and c["actual"] != label for c in cases)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)
    result["overall"][variant] = {
        "cases": len(cases), "correct": sum(case["correct"] for case in cases),
        "accuracy": sum(case["correct"] for case in cases) / len(cases),
        "macro_f1": sum(f1s) / len(f1s),
        "input_tokens": sum(case["input_tokens"] for case in cases),
        "output_tokens": sum(case["output_tokens"] for case in cases),
        "total_tokens": sum(case["total_tokens"] for case in cases),
        "model_calls": sum(case["source"] == "model" for case in cases),
        "command_calls": sum(case["source"] == "command" for case in cases),
    }
n, h = result["overall"]["natural_language"], result["overall"]["hybrid"]
result["overall"]["delta_hybrid_minus_nl"] = {
    "accuracy": h["accuracy"] - n["accuracy"],
    "macro_f1": h["macro_f1"] - n["macro_f1"],
    "total_tokens": h["total_tokens"] - n["total_tokens"],
    "total_token_ratio": h["total_tokens"] / n["total_tokens"],
    "model_calls": h["model_calls"] - n["model_calls"],
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(result, indent=2)+"\n")
