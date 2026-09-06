#!/usr/bin/env python3
"""Run a frozen text-classification SOP against a prepared PLaND eval set."""

from __future__ import annotations

import argparse
import csv
import email.utils
import hashlib
import importlib.util
import json
import math
import os
import re
import resource
import statistics
import time
import uuid
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


STEP = re.compile(r"^\s*\d+[.)].*?pland:(english|reference|command)", re.MULTILINE)
SOP_CONTRACT = Path(__file__).resolve().parents[3] / "skills/pland-evolver/scripts/sop_contract.py"


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


def runtime_contract(args: argparse.Namespace) -> dict[str, Any]:
    return {**args.hosted_config.contract(), "execution_backend": "deepagent",
            "workers": args.workers}


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


def is_rate_limit(error: Exception) -> bool:
    response = getattr(error, "response", None)
    return getattr(error, "status_code", None) == 429 or getattr(response, "status_code", None) == 429


def rate_limit_delay(error: Exception, attempt: int, case_id: str) -> float:
    """Honor Retry-After; otherwise use bounded, case-jittered backoff."""
    response = getattr(error, "response", None)
    headers = getattr(response, "headers", {}) if response is not None else {}
    retry_ms = headers.get("retry-after-ms")
    try:
        delay = float(retry_ms) / 1000 if retry_ms is not None else None
    except (TypeError, ValueError):
        delay = None
    if delay is None:
        retry_after = headers.get("retry-after")
        try:
            delay = float(retry_after) if retry_after is not None else None
        except (TypeError, ValueError):
            try:
                parsed = email.utils.parsedate_to_datetime(retry_after)
                delay = parsed.timestamp() - datetime.now(UTC).timestamp()
            except (TypeError, ValueError, OverflowError):
                delay = None
    if delay is None or not math.isfinite(delay) or delay <= 0:
        jitter = 0.75 + int(hashlib.sha256(case_id.encode()).hexdigest()[:2], 16) / 510
        delay = min(60.0, 2.0 ** min(attempt, 6)) * jitter
    return min(300.0, max(0.1, delay))


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
    parser.add_argument("--max-completion-tokens", type=int,
                        help="Required for hosted execution; includes reasoning and final output")
    parser.add_argument("--request-timeout", type=float, default=300)
    parser.add_argument("--seed", type=int, default=20260902)
    parser.add_argument("--experiment-id")
    parser.add_argument("--run-id")
    parser.add_argument("--candidate-id")
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--resume", action="store_true",
                        help="Resume from OUTPUT.partial.json when present")
    parser.add_argument("--checkpoint-every", type=int, default=10)
    parser.add_argument("--workers", type=int,
                        help="Explicit measured concurrency required for hosted execution")
    parser.add_argument("--limit", type=int,
                        help="Run only the first N selected cases for a smoke test")
    parser.add_argument("--preflight-only", action="store_true",
                        help="Validate and freeze inputs without invoking the model or running cases")
    args = parser.parse_args()
    from hosted_execution import MODEL, HostedConfig, validate_output_path
    if args.max_completion_tokens is None or args.workers is None:
        parser.error("--max-completion-tokens and --workers are required")
    try:
        args.hosted_config = HostedConfig(args.max_completion_tokens, args.request_timeout)
        validate_output_path(args.output)
    except ValueError as error:
        parser.error(str(error))
    args.model = MODEL
    if not args.preflight_only and not os.environ.get("MODEL_API_KEY"):
        parser.error("MODEL_API_KEY is missing from .env")
    if args.output.exists():
        raise SystemExit(f"output exists: {args.output}")
    if args.checkpoint_every < 1:
        raise SystemExit("--checkpoint-every must be positive")
    if args.workers < 1:
        raise SystemExit("--workers must be positive")
    if args.attempt < 1:
        raise SystemExit("--attempt must be positive")

    with (args.dataset / "evals.csv").open(encoding="utf-8", newline="") as handle:
        all_rows = list(csv.DictReader(handle))
    rows = [row for row in all_rows if row["split"] == args.split]
    if args.limit is not None:
        if args.limit < 1:
            raise SystemExit("--limit must be positive")
        rows = rows[:args.limit]
    if not rows or len({row['id'] for row in rows}) != len(rows):
        raise SystemExit("selected split must contain nonempty, unique case IDs")
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
    if classifier:
        if args.baseline_sop is None or not args.command_step_id:
            raise SystemExit("--baseline-sop and --command-step-id are required with --classifier")
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
        baseline_contract = contract_module.baseline_contract(sop)
        sop_contract = {
            "valid": True,
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
    invariant_core["agent_harness_sha256"] = canonical_digest({
        "runner": digest(Path(__file__)),
        "deepagent_execution": digest(Path(__file__).with_name("deepagent_execution.py")),
        "dependencies": digest(Path(__file__).resolve().parents[3] / "reproduce/uv.lock"),
    })
    invariant_core["hosted_adapter_sha256"] = digest(Path(__file__).with_name("hosted_execution.py"))
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
            "runtime": runtime_contract(args),
            "model_identity": args.hosted_config.identity(),
        }
        write_json_atomic(args.output, preflight)
        print(json.dumps(preflight, sort_keys=True))
        return 0
    partial_path = args.output.with_suffix(args.output.suffix + ".partial.json")
    if partial_path.exists() and not args.resume:
        raise SystemExit("partial checkpoint exists; use --resume or a new output path")
    cases: list[dict[str, Any]] = []
    expected_resume = {
        "dataset": str(args.dataset.resolve()), "split": args.split, "model": args.model,
        "seed": args.seed, "system_prompt_sha256": digest(args.system_prompt),
        "sop_sha256": digest(args.sop), "evals_sha256": digest(args.dataset / "evals.csv"),
        "selection_sha256": digest(args.dataset / "selection.json"),
        "classifier_sha256": digest(args.classifier) if args.classifier else None,
        "baseline_sop_sha256": baseline_contract["baseline_sop_sha256"],
        "baseline_sop_contract_sha256": baseline_contract["contract_sha256"],
        "runtime": runtime_contract(args),
    }
    expected_resume["frozen_manifest_sha256"] = frozen_manifest_hash
    expected_resume["model_identity"] = args.hosted_config.identity()
    if args.resume and partial_path.exists():
        partial = json.loads(partial_path.read_text(encoding="utf-8"))
        if partial.get("resume_contract") != expected_resume:
            raise SystemExit("partial checkpoint does not match the requested run")
        cases = partial.get("cases", [])
    if args.resume:
        recovered = {case['id']: case for case in cases}
        receipt_dir = args.output.parent / (args.output.name + '.attempts')
        for receipt in sorted(receipt_dir.glob('*.json')):
            event = json.loads(receipt.read_text(encoding='utf-8'))
            if event.get('frozen_manifest_sha256') != frozen_manifest_hash:
                raise SystemExit('attempt receipt does not match the requested run')
            if event.get('status') == 'completed':
                case = event['case']
                previous = recovered.get(case['id'])
                if previous is not None and previous != case:
                    raise SystemExit('conflicting completed receipts for one case')
                recovered[case['id']] = case
        cases = list(recovered.values())
    if len({c['id'] for c in cases}) != len(cases) or not {c['id'] for c in cases} <= {r['id'] for r in rows}:
        raise SystemExit("checkpoint contains duplicate or unexpected case IDs")
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
                isinstance(predicted.get("matched_rule"), str) and predicted["matched_rule"]
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
                + "Return exactly one JSON object with label."
            )
            from deepagent_execution import invoke
            value, raw = invoke(args.model, system, prompt, labels, args.hosted_config)
            actual = value.get("label") if value.get("label") in labels else None
            matched_rule = None
            parse_error = None if actual is not None else "invalid_prediction_schema"
            if raw.get("done_reason") == "length":
                parse_error = "model_output_truncated"
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
        case = {
            "id": row["id"], "expected": expected, "actual": actual,
            "correct": actual == expected, "source": source, "matched_rule": matched_rule,
            "parse_error": parse_error,
            "raw_message_content": raw.get("message", {}).get("content"),
            "latency_seconds": elapsed,
            "input_tokens": raw.get("prompt_eval_count", 0),
            "output_tokens": raw.get("eval_count", 0),
            "total_tokens": raw.get("prompt_eval_count", 0) + raw.get("eval_count", 0),
            "model_calls": raw.get("model_calls", int(source == "model")),
            "model_done_reason": raw.get("done_reason"),
            "deepagent_trace": raw.get("deepagent_trace", []),
            "step_trace": step_trace,
        }
        for key in ("reasoning_tokens", "cached_input_tokens", "service_cost_usd"):
            case[key] = raw.get(key) if source == "model" else 0
        case["request_receipts"] = raw.get("request_receipts", [])
        return case

    def checkpoint():
        write_json_atomic(partial_path, {"schema_version": 1,
                          "resume_contract": expected_resume, "cases": cases})

    def recorded_case(row):
        """Durable receipts preserve completed work even if another worker fails."""
        receipt = args.output.parent / (args.output.name + ".attempts") / (uuid.uuid4().hex + ".json")
        event = {"case_id": row["id"], "started_at": datetime.now(UTC).isoformat(),
                 "frozen_manifest_sha256": frozen_manifest_hash, "status": "started"}
        write_json_atomic(receipt, event)
        rate_limit_retries = []
        while True:
            try:
                case = run_case(row)
                break
            except Exception as error:
                if is_rate_limit(error):
                    delay = rate_limit_delay(error, len(rate_limit_retries) + 1, row["id"])
                    rate_limit_retries.append({
                        "attempt": len(rate_limit_retries) + 1,
                        "observed_at": datetime.now(UTC).isoformat(),
                        "delay_seconds": delay,
                    })
                    event.update(status="rate_limited_retry", rate_limit_retries=rate_limit_retries)
                    write_json_atomic(receipt, event)
                    time.sleep(delay)
                    continue
                # Provider exception text may contain request content or credentials.
                event.update(status="failed", error_type=type(error).__name__,
                             status_code=getattr(error, "status_code", None),
                             billing_status="unknown", ended_at=datetime.now(UTC).isoformat())
                write_json_atomic(receipt, event)
                raise RuntimeError(f"hosted-model case failed; inspect receipt {receipt}") from None
        event.update(status="completed", case=case, rate_limit_retries=rate_limit_retries,
                     ended_at=datetime.now(UTC).isoformat())
        write_json_atomic(receipt, event)
        return case

    pending_rows = [row for row in rows if row["id"] not in completed_ids]
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        checkpoint()

        def completed():
            remaining = iter(pending_rows)
            futures = set()

            def refill():
                while len(futures) < args.workers:
                    row = next(remaining, None)
                    if row is None:
                        break
                    futures.add(executor.submit(recorded_case, row))

            refill()
            try:
                while futures:
                    done, _ = wait(futures, return_when=FIRST_COMPLETED)
                    for future in done:
                        futures.remove(future)
                        yield future.result()
                    refill()
            except Exception:
                for pending in futures:
                    pending.cancel()
                checkpoint()
                raise
        results = completed()
        for case in results:
            cases.append(case)
            actual = case["actual"]
            expected = case["expected"]
            print(json.dumps({"id": case["id"], "correct": actual == expected, "source": case["source"]}))
            checkpoint()

    row_order = {row['id']: index for index, row in enumerate(rows)}
    cases.sort(key=lambda case: row_order[case['id']])

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
    payload = {
        "schema_version": 1, "created_at": datetime.now(UTC).isoformat(),
        "experiment_id": experiment_id, "run_id": run_id,
        "candidate_id": candidate_id, "attempt": args.attempt,
        "dataset": args.dataset.name, "split": args.split, "model": args.model,
        "model_digest": None,
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
    from hosted_execution import optional_sum
    payload['model_identity'] = args.hosted_config.identity()
    providers = sorted({r['provider'] for c in cases for r in c['request_receipts']})
    payload['observed_providers'] = providers
    if len(providers) > 1:
        raise SystemExit('provider changed within the run; retained checkpoint and receipts')
    for key in ('reasoning_tokens', 'cached_input_tokens', 'service_cost_usd'):
        payload['summary'][key] = optional_sum([c[key] for c in cases])
    payload['summary']['estimated_model_cost_usd'] = payload['summary']['service_cost_usd']
    write_json_atomic(args.output, payload)
    partial_path.unlink(missing_ok=True)
    print(json.dumps(payload["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
