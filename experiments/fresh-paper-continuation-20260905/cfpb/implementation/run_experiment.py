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
SOP_CONTRACT = Path(__file__).resolve().parents[3] / "skills/pland-evolver/scripts/sop_contract.py"
HISTORICAL_NL_SOPS = {
    "965f61f435c835e6412425f52045395e24f04edbe32f1fd7327d8c64aaaa9044",
    "85c7d9b4c375bb8921599fef0e59fc863b84cccbf800304f978e3c8bf90a9d2b",
    "d2cdab135f281ad33df35eec3f3e29569128766130c73a2f14658565d62b8bac",
}
HISTORICAL_HYBRIDS = {
    ("bae5dc5a878689973b03be0443960cf8086a106819a770fd18ca454d0aa321cc", "3ec37d6e8a0ccf6a9f43acb0f222f85b985b06659a09ff271dfac8cbee2a955c"),
    ("8d9adc2a8a0b06c5bd372c9303d4c2879208f9584e4b5d86c621e53f21d9430a", "7ccb07ea31e867964779b93deda9f8689a6ce87c2c779caaaf96beed54637b83"),
    ("6b48ce6370be4f3c97c80b23acb55a70fdfd1e93eb7ed56ba24acf92302e1caa", "8f74f7910d956daf511dbdd373fa687ca990989b33fecd377c5c4d7011cfb74e"),
    ("fc38770893aab14c8503946784de6d601fd8a4f7d08e093c8a38685835158c34", "b64e68211bbb31003d03c780c89de76a899cdd36bffe7f3158e9564eee4c5328"),
    ("3f9edbe0b03fd5cc6d8ce2cb023cc4e7568969fa722bafdbe0aabb19ef0c2589", "c4d434380e56589562fce0d4e2b8b905dfd3f7ab803bcb55fdf8cc3193810de8"),
    ("1aff4ea73f77ab0000036bd43455221e13ca6681673e913d44f5295100c3db1d", "9416c59d6830ed2291d204326fe5574d76639c179988c574b9176c2235c2a752"),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def datasource_digest(dataset: Path, rows: list[dict[str, str]]) -> str:
    files = []
    for row in sorted(rows, key=lambda item: item["id"]):
        path = dataset / row["input"]
        files.append({"id": row["id"], "input": row["input"], "sha256": digest(path)})
    return canonical_digest(files)


def skill_content_digest(sop: Path, classifier: Path | None) -> str:
    files = [{"role": "SKILL.md", "sha256": digest(sop)}]
    if classifier is not None:
        files.append({"role": "classifier", "sha256": digest(classifier)})
    return canonical_digest(files)


def ollama(
    model: str,
    system: str,
    prompt: str,
    seed: int,
    labels: list[str],
    num_ctx: int,
    num_predict: int,
    keep_alive: int,
    historical_confidence_schema: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    schema = {
        "type": "object",
        "properties": {
            "label": {"type": "string", "enum": labels},
        },
        "required": ["label"],
        "additionalProperties": False,
    }
    if historical_confidence_schema:
        schema["properties"]["confidence"] = {"type": "number", "minimum": 0, "maximum": 1}
        schema["required"].append("confidence")
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
        "execution_backend": getattr(args, "execution_backend", "ollama"),
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


def load_sop_contract_module():
    spec = importlib.util.spec_from_file_location("pland_sop_contract", SOP_CONTRACT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load SOP contract validator: {SOP_CONTRACT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
    parser.add_argument("--baseline-sop", type=Path,
                        help="Frozen English baseline; required for a command candidate")
    parser.add_argument("--command-step-id",
                        help="Stable command node linked to its exact English fallback")
    parser.add_argument("--model", default="qwen3:14b")
    parser.add_argument("--execution-backend", choices=("ollama", "deepagent"), default="ollama")
    parser.add_argument("--seed", type=int, default=20260902)
    parser.add_argument("--experiment-id")
    parser.add_argument("--run-id")
    parser.add_argument("--candidate-id")
    parser.add_argument("--attempt", type=int, default=1)
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
    parser.add_argument("--preflight-only", action="store_true",
                        help="Validate and freeze inputs without invoking the model or running cases")
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"output exists: {args.output}")
    if args.checkpoint_every < 1:
        raise SystemExit("--checkpoint-every must be positive")
    if args.workers < 1 or args.num_ctx < 1 or args.num_predict < 1:
        raise SystemExit("--workers, --num-ctx, and --num-predict must be positive")
    if args.attempt < 1:
        raise SystemExit("--attempt must be positive")

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
    experiment_id = args.experiment_id or args.dataset.name
    run_id = args.run_id or args.output.stem
    candidate_id = args.candidate_id or ("hybrid" if classifier else "baseline")
    if classifier is None and candidate_id != "baseline":
        raise SystemExit("a natural-language run must use candidate-id baseline")
    if classifier is not None and candidate_id == "baseline":
        raise SystemExit("a hybrid run cannot use candidate-id baseline")
    contract_module = load_sop_contract_module()
    sop_hash = digest(args.sop)
    classifier_hash = digest(args.classifier) if args.classifier else None
    legacy_evidence_replay = (
        (classifier is None and sop_hash in HISTORICAL_NL_SOPS)
        or (classifier is not None and (sop_hash, classifier_hash) in HISTORICAL_HYBRIDS)
    )
    if classifier:
        if legacy_evidence_replay:
            baseline_content = sop
            legacy_contract_hash = hashlib.sha256(
                f"historical:{sop_hash}:{classifier_hash}".encode()
            ).hexdigest()
            baseline_contract = {
                "baseline_sop_sha256": sop_hash,
                "contract_sha256": legacy_contract_hash,
            }
            sop_contract = {"valid": False, "historical_evidence_replay": True,
                            "baseline_contract_sha256": legacy_contract_hash,
                            "command_fallback_links": []}
        elif args.baseline_sop is None or not args.command_step_id:
            raise SystemExit("--baseline-sop and --command-step-id are required with --classifier")
        else:
            baseline_content = args.baseline_sop.read_text(encoding="utf-8")
            baseline_contract = contract_module.baseline_contract(baseline_content)
            sop_contract = contract_module.validate_candidate(sop, baseline_contract)
            linked_ids = {
                item["command_step_id"] for item in sop_contract["command_fallback_links"]
            }
            if args.command_step_id not in linked_ids:
                raise SystemExit("--command-step-id is not a validated command/fallback link")
    else:
        if args.command_step_id:
            raise SystemExit("--command-step-id requires --classifier")
        baseline_content = sop
        if legacy_evidence_replay:
            legacy_contract_hash = hashlib.sha256(f"historical:{sop_hash}".encode()).hexdigest()
            baseline_contract = {"baseline_sop_sha256": sop_hash,
                                 "contract_sha256": legacy_contract_hash}
        else:
            baseline_contract = contract_module.baseline_contract(sop)
        sop_contract = {
            "valid": not legacy_evidence_replay,
            "historical_evidence_replay": legacy_evidence_replay,
            "baseline_contract_sha256": baseline_contract["contract_sha256"],
            "baseline_sop_sha256": baseline_contract["baseline_sop_sha256"],
            "candidate_sop_sha256": digest(args.sop),
            "command_fallback_links": [],
        }
    data_hash = datasource_digest(args.dataset, all_rows)
    skill_hash = skill_content_digest(args.sop, args.classifier)
    invariant_core = {
        "system_prompt_sha256": digest(args.system_prompt),
        "evals_sha256": digest(args.dataset / "evals.csv"),
        "selection_sha256": digest(args.dataset / "selection.json"),
        "datasource_snapshot_sha256": data_hash,
        "scorer_sha256": digest(Path(__file__)),
        "agent_harness_sha256": digest(Path(__file__)),
        "baseline_sop_sha256": baseline_contract["baseline_sop_sha256"],
        "baseline_sop_contract_sha256": baseline_contract["contract_sha256"],
    }
    if args.execution_backend == "deepagent":
        invariant_core["agent_harness_sha256"] = canonical_digest({
            "runner": digest(Path(__file__)),
            "deepagent_execution": digest(Path(__file__).with_name("deepagent_execution.py")),
            "dependencies": digest(Path(__file__).resolve().parents[3] / "reproduce/uv.lock"),
        })
    frozen_manifest_hash = canonical_digest({
        **invariant_core,
        "model": args.model,
        "seed": args.seed,
        "runtime": runtime_contract(args),
    })
    if args.preflight_only:
        for row in rows:
            payload = json.loads((args.dataset / row["input"]).read_text(encoding="utf-8"))
            if not any(isinstance(payload.get(key), str) and payload[key].strip()
                       for key in ("text", "narrative", "raw_email")):
                raise SystemExit(f"case {row['id']} has no supported text input")
            if json.loads(row["output"]).get("label") not in labels:
                raise SystemExit(f"case {row['id']} has an invalid expected label")
        preflight = {
            "schema_version": 1,
            "status": "ready_for_model_run",
            "model_invoked": False,
            "cases_inspected": len(rows),
            "split": args.split,
            "model": args.model,
            "seed": args.seed,
            "experiment_id": experiment_id,
            "run_id": run_id,
            "candidate_id": candidate_id,
            "attempt": args.attempt,
            "sop_sha256": sop_hash,
            "skill_content_sha256": skill_hash,
            "frozen_manifest_sha256": frozen_manifest_hash,
            "invariants": {**invariant_core, "evaluation_sha256": invariant_core["evals_sha256"]},
            "sop_contract": sop_contract,
        }
        write_json_atomic(args.output, preflight)
        print(json.dumps(preflight, sort_keys=True))
        return 0
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
            "baseline_sop_sha256": baseline_contract["baseline_sop_sha256"],
            "baseline_sop_contract_sha256": baseline_contract["contract_sha256"],
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
        command_error = None
        try:
            predicted = classifier(text, labels) if classifier else None
        except Exception as error:  # A command failure must escape, not abort the paired run.
            predicted = None
            command_error = f"{type(error).__name__}: {error}"
        if (
            isinstance(predicted, dict)
            and predicted.get("label") in labels
            and (
                legacy_evidence_replay
                or (isinstance(predicted.get("matched_rule"), str) and predicted["matched_rule"])
            )
        ):
            actual = predicted["label"]
            matched_rule = predicted.get("matched_rule")
            source = "command"
            parse_error = None
            step_trace = {
                "command_step_id": args.command_step_id,
                "fallback_step_id": None,
                "fallback_instruction_sha256": None,
                "escape_reason": None,
                "command_work": True,
                "model_work": False,
                "command_error": None,
            }
        else:
            link = next(
                (item for item in sop_contract["command_fallback_links"]
                 if item["command_step_id"] == args.command_step_id),
                None,
            )
            escape_reason = (
                "command_execution_failed" if command_error
                else "command_abstained" if predicted is None
                else "command_output_guard_failed"
            ) if classifier else None
            prompt = (
                f"Workflow SOP:\n{baseline_content}\n\nAllowed labels:\n{json.dumps(labels)}\n\n"
                f"Classify this document:\n{text}\n\n"
                + ("Return exactly one JSON object with label and confidence."
                   if legacy_evidence_replay else "Return exactly one JSON object with label.")
            )
            if args.execution_backend == "deepagent":
                from deepagent_execution import invoke
                value, raw = invoke(args.model, system, prompt, args.seed, labels,
                                    args.num_ctx, args.num_predict, args.keep_alive)
            else:
                value, raw = ollama(
                    args.model, system, prompt, args.seed, labels,
                    args.num_ctx, args.num_predict, args.keep_alive, legacy_evidence_replay,
                )
            actual = value.get("label") if value.get("label") in labels else None
            matched_rule = None
            parse_error = None if actual is not None else "invalid_prediction_schema"
            if raw.get("done_reason") == "length":
                parse_error = "model_output_truncated"
            if raw.get("prompt_eval_count", 0) >= args.num_ctx - args.num_predict:
                parse_error = "context_capacity_reached"
            step_trace = {
                "command_step_id": args.command_step_id,
                "fallback_step_id": link["fallback_step_id"] if link else None,
                "fallback_instruction_sha256": (
                    link["fallback_instruction_sha256"] if link else None
                ),
                "escape_reason": escape_reason,
                "command_work": bool(classifier),
                "model_work": True,
                "command_error": command_error,
            }
        elapsed = time.perf_counter() - started
        return {
            "id": row["id"], "expected": expected, "actual": actual,
            "correct": actual == expected, "source": source, "matched_rule": matched_rule,
            "parse_error": parse_error,
            "raw_message_content": raw.get("message", {}).get("content"),
            "latency_seconds": elapsed,
            "input_tokens": raw.get("prompt_eval_count", 0),
            "output_tokens": raw.get("eval_count", 0),
            "total_tokens": raw.get("prompt_eval_count", 0) + raw.get("eval_count", 0),
            "ollama_load_ns": raw.get("load_duration", 0),
            "ollama_prompt_ns": raw.get("prompt_eval_duration", 0),
            "ollama_eval_ns": raw.get("eval_duration", 0),
            "model_calls": raw.get("model_calls", int(source == "model")),
            "model_done_reason": raw.get("done_reason"),
            "deepagent_trace": raw.get("deepagent_trace", []),
            "step_trace": step_trace,
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
                        "baseline_sop_sha256": baseline_contract["baseline_sop_sha256"],
                        "baseline_sop_contract_sha256": baseline_contract["contract_sha256"],
                        "runtime": runtime_contract(args),
                    },
                    "cases": cases,
                })

    latencies = [case["latency_seconds"] for case in cases]
    correct = sum(case["correct"] for case in cases)
    representations = Counter(STEP.findall(sop))
    error_counts = {
        "invalid_prediction_schema": sum(
            c["parse_error"] == "invalid_prediction_schema" for c in cases
        ),
        "command_execution_failed": sum(
            c["step_trace"]["escape_reason"] == "command_execution_failed" for c in cases
        ),
        "model_output_truncated": sum(c["parse_error"] == "model_output_truncated" for c in cases),
        "context_capacity_reached": sum(c["parse_error"] == "context_capacity_reached" for c in cases),
    }
    error_counts = {name: count for name, count in error_counts.items() if count}
    resolved_model_digest = model_digest(args.model)
    payload = {
        "schema_version": 1, "created_at": datetime.now(UTC).isoformat(),
        "experiment_id": experiment_id, "run_id": run_id,
        "candidate_id": candidate_id, "attempt": args.attempt,
        "dataset": args.dataset.name, "split": args.split, "model": args.model,
        "model_digest": resolved_model_digest,
        "seed": args.seed,
        "evals": str((args.dataset / "evals.csv").resolve()),
        "evals_sha256": invariant_core["evals_sha256"],
        "sop_sha256": sop_hash,
        "skill_content_sha256": skill_hash,
        "frozen_manifest_sha256": frozen_manifest_hash,
        "quality_metric": "accuracy",
        "runtime": runtime_contract(args),
        "invariants": {**invariant_core, "evaluation_sha256": invariant_core["evals_sha256"]},
        "sop": {
            "variant": "hybrid" if classifier else "natural_language",
            "sha256": digest(args.sop),
            "classifier_sha256": digest(args.classifier) if args.classifier else None,
            "content": sop,
            "step_representations": dict(representations),
            "contract": sop_contract,
        },
        "summary": {
            "cases": len(cases), "correct": correct, "accuracy": correct / len(cases),
            "macro_f1": macro_f1(cases, labels),
            "input_tokens": sum(c["input_tokens"] for c in cases),
            "output_tokens": sum(c["output_tokens"] for c in cases),
            "total_tokens": sum(c["total_tokens"] for c in cases),
            "estimated_model_cost_usd": 0.0,
            "model_calls": sum(c.get("model_calls", int(c["source"] == "model")) for c in cases),
            "model_tokens": sum(c["total_tokens"] for c in cases if c["source"] == "model"),
            "command_calls": sum(c["step_trace"]["command_work"] for c in cases),
            "command_resolved_cases": sum(c["source"] == "command" for c in cases),
            "fallback_model_calls": sum(
                c["step_trace"]["escape_reason"] is not None for c in cases
            ),
            "fallback_model_tokens": sum(
                c["total_tokens"] for c in cases
                if c["step_trace"]["escape_reason"] is not None
            ),
            "normal_completion_rate": sum(c["actual"] is not None for c in cases) / len(cases),
            "errors": error_counts,
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
