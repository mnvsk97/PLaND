#!/usr/bin/env python3
"""Aggregate repeated paired PLaND classification runs."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
import statistics
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SEEDS = (20260903, 20260904, 20260905)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def distribution(values: list[float]) -> dict[str, Any]:
    ordered = sorted(values)
    return {
        "values": values,
        "mean": statistics.fmean(values),
        "sample_sd": statistics.stdev(values) if len(values) > 1 else None,
        "min": ordered[0],
        "max": ordered[-1],
        "range": ordered[-1] - ordered[0],
    }


def quantiles(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    def percentile(probability: float) -> float:
        position = (len(ordered) - 1) * probability
        lower = int(position)
        upper = min(lower + 1, len(ordered) - 1)
        fraction = position - lower
        return ordered[lower] * (1 - fraction) + ordered[upper] * fraction
    return {
        "min": ordered[0], "median": percentile(0.5), "mean": statistics.fmean(ordered),
        "p95": percentile(0.95), "max": ordered[-1],
    }


def case_map(run: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {case["id"]: case for case in run["cases"]}


def stability(runs: list[dict[str, Any]], identifiers: list[str]) -> dict[str, Any]:
    maps = [case_map(run) for run in runs]
    disagreements = [identifier for identifier in identifiers
                     if len({mapping[identifier].get("actual") for mapping in maps}) > 1]
    pairwise = []
    for left, right in itertools.combinations(range(len(runs)), 2):
        count = sum(maps[left][identifier].get("actual") != maps[right][identifier].get("actual")
                    for identifier in identifiers)
        pairwise.append({
            "left_seed": runs[left]["seed"], "right_seed": runs[right]["seed"],
            "disagreement_cases": count, "disagreement_fraction": count / len(identifiers),
        })
    return {
        "cases": len(identifiers), "all_runs_agree_cases": len(identifiers) - len(disagreements),
        "any_disagreement_cases": len(disagreements),
        "any_disagreement_fraction": len(disagreements) / len(identifiers),
        "disagreement_case_ids": disagreements,
        "pairwise": pairwise,
    }


def aggregate_dataset(directory: Path) -> dict[str, Any]:
    runs = {
        variant: [json.loads((directory / f"seed-{seed}-{variant}.json").read_text(encoding="utf-8"))
                  for seed in SEEDS]
        for variant in ("nl", "hybrid")
    }
    identifiers = sorted(case_map(runs["nl"][0]))
    reference = runs["nl"][0]
    for variant_runs in runs.values():
        for run in variant_runs:
            if sorted(case_map(run)) != identifiers:
                raise ValueError("case identifiers differ across runs")
            for key in ("dataset", "split", "model", "model_digest", "runtime", "invariants"):
                if run.get(key) != reference.get(key):
                    raise ValueError(f"frozen contract differs across runs: {key}")
    for index, seed in enumerate(SEEDS):
        if runs["nl"][index].get("seed") != seed or runs["hybrid"][index].get("seed") != seed:
            raise ValueError(f"paired seed mismatch: {seed}")
    for variant, variant_runs in runs.items():
        sop_contract = variant_runs[0]["sop"]
        for run in variant_runs[1:]:
            if run["sop"] != sop_contract:
                raise ValueError(f"{variant} SOP contract differs across seeds")
    variants = {}
    for variant, variant_runs in runs.items():
        variants[variant] = {
            "accuracy": distribution([run["summary"]["accuracy"] for run in variant_runs]),
            "total_tokens": distribution([run["summary"]["total_tokens"] for run in variant_runs]),
            "model_calls": distribution([run["summary"]["model_calls"] for run in variant_runs]),
            "per_case_tokens": quantiles([
                case["total_tokens"] for run in variant_runs for case in run["cases"]
            ]),
            "per_case_latency_seconds": quantiles([
                case["latency_seconds"] for run in variant_runs for case in run["cases"]
            ]),
            "prediction_stability": stability(variant_runs, identifiers),
        }

    hybrid_maps = [case_map(run) for run in runs["hybrid"]]
    route_signatures = {identifier: tuple(mapping[identifier]["source"] for mapping in hybrid_maps)
                        for identifier in identifiers}
    route_counts = Counter(route_signatures.values())
    strata = {}
    for label, wanted in (("deterministic_command", ("command",) * 3),
                          ("model_fallback", ("model",) * 3)):
        selected = [identifier for identifier, signature in route_signatures.items() if signature == wanted]
        strata[label] = stability(runs["hybrid"], selected) if selected else {"cases": 0}
    unstable_routes = [identifier for identifier, signature in route_signatures.items()
                       if len(set(signature)) > 1]

    paired = []
    comparisons = []
    for index, seed in enumerate(SEEDS):
        nl_map, hybrid_map = case_map(runs["nl"][index]), case_map(runs["hybrid"][index])
        count = sum(nl_map[identifier].get("actual") != hybrid_map[identifier].get("actual")
                    for identifier in identifiers)
        paired.append({"seed": seed, "prediction_disagreement_cases": count,
                       "prediction_disagreement_fraction": count / len(identifiers)})
        comparison_path = directory / f"seed-{seed}-comparison.json"
        comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
        comparisons.append({"seed": seed, "gate": comparison["gate"],
                            "accuracy_difference_bootstrap_95": comparison["paired_statistics"]["accuracy_difference_bootstrap_95"],
                            "token_reduction_bootstrap_95": comparison["paired_statistics"]["token_reduction_bootstrap_95"],
                            "token_reduction_fraction": comparison["delta_hybrid_minus_nl"]["token_reduction_fraction"]})
    return {
        "cases_per_run": len(identifiers), "seeds": list(SEEDS),
        "frozen_contract_verified": True,
        "frozen_contract": {key: reference.get(key) for key in
                            ("dataset", "split", "model", "model_digest", "runtime", "invariants")},
        "variant_hashes": {variant: {key: value for key, value in variant_runs[0]["sop"].items()
                                     if key != "content"}
                           for variant, variant_runs in runs.items()},
        "variants": variants,
        "paired_nl_hybrid_prediction_disagreement": paired,
        "hybrid_route_stability": {
            "signature_counts": {"/".join(key): value for key, value in sorted(route_counts.items())},
            "unstable_route_cases": len(unstable_routes), "unstable_route_case_ids": unstable_routes,
            "prediction_disagreement_by_stable_route": strata,
        },
        "per_run_gates": comparisons,
    }


def write_manifest(directory: Path) -> None:
    manifest_path = directory / "manifest.json"
    files = [path for path in directory.iterdir() if path.is_file() and path != manifest_path]
    payload = {
        "schema_version": 1, "created_at": datetime.now(UTC).isoformat(),
        "algorithm": "sha256", "files": [
            {"path": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in sorted(files)
        ],
    }
    if manifest_path.exists():
        raise FileExistsError(manifest_path)
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_recursive_manifest(directory: Path) -> None:
    manifest_path = directory / "study-manifest.json"
    files = [path for path in directory.rglob("*")
             if path.is_file() and path != manifest_path and "__pycache__" not in path.parts]
    payload = {
        "schema_version": 1, "created_at": datetime.now(UTC).isoformat(),
        "algorithm": "sha256", "files": [
            {"path": path.relative_to(directory).as_posix(), "bytes": path.stat().st_size,
             "sha256": sha256(path)} for path in sorted(files)
        ],
    }
    if manifest_path.exists():
        raise FileExistsError(manifest_path)
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_readme(directory: Path, result: dict[str, Any]) -> None:
    path = directory / "README.md"
    if path.exists():
        raise FileExistsError(path)
    nl = result["variants"]["nl"]
    hybrid = result["variants"]["hybrid"]
    lines = [
        f"# {directory.parents[1].name} three-run variance evidence",
        "",
        "This folder contains three new paired replications under the frozen optimized",
        "runtime. These runs are descriptive replication evidence, not new untouched tests.",
        "The original sequential results are not pooled because runtime conditions differ.",
        "",
        "## Summary",
        "",
        f"- Cases per run: {result['cases_per_run']}",
        f"- Seeds: {', '.join(str(seed) for seed in result['seeds'])}",
        f"- NL accuracy mean (sample SD; range): {nl['accuracy']['mean']:.4f} "
        f"({nl['accuracy']['sample_sd']:.4f}; {nl['accuracy']['min']:.4f}-{nl['accuracy']['max']:.4f})",
        f"- Hybrid accuracy mean (sample SD; range): {hybrid['accuracy']['mean']:.4f} "
        f"({hybrid['accuracy']['sample_sd']:.4f}; {hybrid['accuracy']['min']:.4f}-{hybrid['accuracy']['max']:.4f})",
        "",
        "With only three seeds, these values characterize the observed frozen condition;",
        "they do not support a significance or broad generalization claim.",
        "",
        "## Reproduce and inspect",
        "",
        "Run `experiments/variance-study/run_variance_study.py` using the exact command in",
        "`experiments/variance-study/README.md`. `run-ledger.json` records each expanded",
        "command, order, start/end timestamp, exit status, and log checksum. Each",
        "`seed-*-nl.json` or `seed-*-hybrid.json` stores per-case prediction, correctness,",
        "tokens, latency, and routing source. Each paired comparison applies the frozen",
        "absolute viability, non-inferiority, and efficiency gates.",
        "",
        "`manifest.json` gives the byte size and SHA-256 checksum of every artifact in this",
        "folder. Prepared source text stays in ignored `tmp/`; the content audit recorded in",
        "the cross-study summary confirms that committed JSON contains no source-text fields.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def audit_safe_results(directory: Path) -> dict[str, Any]:
    forbidden_keys = {"text", "narrative", "raw_email", "source_text", "input_content"}
    findings = []
    secret_patterns = {
        "openai_key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{16,}"),
        "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
        "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
        "private_key": re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY"),
    }
    secret_findings = []
    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key in forbidden_keys:
                    findings.append(f"{path}.{key}")
                walk(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")
    for path in sorted(directory.glob("*.json")):
        if path.name == "manifest.json":
            continue
        content = path.read_text(encoding="utf-8")
        walk(json.loads(content), path.name)
        for label, pattern in secret_patterns.items():
            if pattern.search(content):
                secret_findings.append({"path": path.name, "pattern": label})
    return {"passed": not findings and not secret_findings,
            "forbidden_source_content_keys": findings,
            "secret_pattern_findings": secret_findings,
            "note": "Run payloads contain identifiers, expected/predicted labels, metrics, routing, SOP snapshots, and model response labels; prepared source records remain outside Git. The audit checks forbidden source-content keys and common credential patterns, but cannot prove absence of every possible secret format."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--study-dir", action="append", required=True, type=Path)
    parser.add_argument("--write-manifests", action="store_true")
    args = parser.parse_args()
    result = {"schema_version": 1, "created_at": datetime.now(UTC).isoformat(),
              "study_design": {"replications": 3, "seeds": list(SEEDS),
                               "uncertainty_note": "Three runs describe observed variability; they do not establish statistical significance or generalize beyond the frozen model, data, and runtime."},
              "datasets": {}}
    for directory in args.study_dir:
        dataset = directory.parents[1].name
        safety = audit_safe_results(directory)
        if not safety["passed"]:
            raise ValueError(f"unsafe result payload: {safety}")
        dataset_result = {**aggregate_dataset(directory), "content_safety_audit": safety,
                          "artifact_directory": str(directory.resolve().relative_to(Path.cwd().resolve()))}
        result["datasets"][dataset] = dataset_result
        if args.write_manifests:
            write_readme(directory, dataset_result)
            write_manifest(directory)
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if args.write_manifests:
        write_recursive_manifest(args.output.parent)
    print(json.dumps({"datasets": list(result["datasets"]), "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
