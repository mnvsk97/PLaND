#!/usr/bin/env python3
"""Compare frozen NL and hybrid text-classification runs."""
import argparse, json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--nl", required=True, type=Path)
parser.add_argument("--hybrid", required=True, type=Path)
parser.add_argument("--output", required=True, type=Path)
args = parser.parse_args()
nl, hybrid = (json.loads(path.read_text()) for path in (args.nl, args.hybrid))
for key in ("dataset", "split", "model", "model_digest", "seed"):
    if nl[key] != hybrid[key]: raise SystemExit(f"invariant mismatch: {key}")
for key in ("system_prompt_sha256", "evals_sha256", "selection_sha256", "scorer_sha256"):
    if nl["invariants"][key] != hybrid["invariants"][key]: raise SystemExit(f"invariant mismatch: {key}")
n, h = nl["summary"], hybrid["summary"]
result = {"natural_language": n, "hybrid": h, "delta_hybrid_minus_nl": {
    "accuracy": h["accuracy"]-n["accuracy"], "macro_f1": h["macro_f1"]-n["macro_f1"],
    "total_tokens": h["total_tokens"]-n["total_tokens"],
    "mean_latency_seconds": h["latency_seconds"]["mean"]-n["latency_seconds"]["mean"],
    "model_calls": h["model_calls"]-n["model_calls"],
}, "invariants": nl["invariants"]}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(result, indent=2)+"\n")
print(json.dumps(result["delta_hybrid_minus_nl"], sort_keys=True))
