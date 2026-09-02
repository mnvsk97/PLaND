#!/usr/bin/env python3
"""Run frozen classification evals against one generated PLaND agent."""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import importlib.util
import json
import os
import re
import statistics
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


CANONICAL_LABELS = {
    "advertisement", "email", "form", "letter", "memo",
    "news", "note", "report", "resume", "scientific",
}
STEP_PATTERN = re.compile(r"^\s*\d+[.)]\s+(.+)$")
REPRESENTATION_PATTERN = re.compile(r"<!--\s*pland:(english|reference|command)\s*-->")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", required=True, type=Path)
    parser.add_argument("--evals", required=True, type=Path)
    parser.add_argument("--split", required=True, choices=("development", "validation"))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--model", default="qwen3:14b")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def ollama_digest(model: str) -> str | None:
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=5) as response:
            payload = json.load(response)
    except (OSError, ValueError):
        return None
    for item in payload.get("models", []):
        if item.get("name") == model or item.get("model") == model:
            return item.get("digest")
    return None


def load_agent(agent_dir: Path):
    resolved = agent_dir.resolve()
    sys.path.insert(0, str(resolved))
    spec = importlib.util.spec_from_file_location("pland_generated_agent", resolved / "agent.py")
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load generated agent: {resolved}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HarnessNormalizer(ast.NodeTransformer):
    """Remove only the SOP tool wiring that candidates are allowed to change."""

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module and node.module.startswith("tools."):
            return None
        return self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        node = self.generic_visit(node)
        name = getattr(node.func, "id", None)
        if name == "create_deep_agent":
            node.keywords = [item for item in node.keywords if item.arg != "tools"]
        return node


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def frozen_invariants(agent_dir: Path, evals: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    root = agent_dir.resolve()
    prompt_path = root / "instructions.md"
    prompt_content = prompt_path.read_text(encoding="utf-8")
    agent_tree = ast.parse((root / "agent.py").read_text(encoding="utf-8"))
    normalized_tree = HarnessNormalizer().visit(agent_tree)
    ast.fix_missing_locations(normalized_tree)
    harness_fingerprint = ast.dump(normalized_tree, annotate_fields=True, include_attributes=False)
    manifest = json.loads((root / "data" / "manifest.json").read_text(encoding="utf-8"))
    datasource_snapshot = json.dumps(manifest["sources"], sort_keys=True, separators=(",", ":"))
    system_prompt = {
        "path": "instructions.md",
        "sha256": sha256_bytes(prompt_content.encode("utf-8")),
        "content": prompt_content,
    }
    invariants = {
        "system_prompt_sha256": system_prompt["sha256"],
        "agent_harness_sha256": sha256_bytes(harness_fingerprint.encode("utf-8")),
        "datasource_snapshot_sha256": sha256_bytes(datasource_snapshot.encode("utf-8")),
        "evaluation_sha256": sha256_bytes(evals.read_bytes()),
        "scorer_sha256": sha256_bytes(Path(__file__).read_bytes()),
    }
    return system_prompt, invariants


def sop_snapshot(agent_dir: Path) -> dict[str, Any]:
    root = agent_dir.resolve()
    skills = sorted(root.glob("skills/*/SKILL.md"))
    if len(skills) != 1:
        raise RuntimeError(f"expected exactly one workflow SOP, found {len(skills)}")
    path = skills[0]
    content = path.read_text(encoding="utf-8")
    counts = {"english": 0, "reference": 0, "command": 0}
    explicit = 0
    for line in content.splitlines():
        match = STEP_PATTERN.match(line)
        if not match:
            continue
        step = match.group(1)
        marker = REPRESENTATION_PATTERN.search(step)
        if marker:
            representation = marker.group(1)
            explicit += 1
        elif re.search(r"\[[^]]+\]\([^)]*\.md(?:#[^)]*)?\)", step):
            representation = "reference"
        elif re.search(r"`(?:python(?:3)?|bash|sh)\s+[^`]+`", step):
            representation = "command"
        else:
            representation = "english"
        counts[representation] += 1
    total = sum(counts.values())
    variant = (
        "natural_language"
        if counts["command"] == 0
        else "hybrid"
        if counts["english"] + counts["reference"] > 0
        else "command_only"
    )
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "content": content,
        "step_representations": {"total": total, **counts},
        "variant": variant,
        "explicitly_annotated_steps": explicit,
    }


def serialize_message(message: Any) -> dict[str, Any]:
    usage = getattr(message, "usage_metadata", None) or {}
    return {
        "type": type(message).__name__,
        "name": getattr(message, "name", None),
        "content": message.content,
        "tool_calls": getattr(message, "tool_calls", None),
        "usage": usage,
        "response_metadata": getattr(message, "response_metadata", None),
    }


def parse_prediction(content: Any) -> tuple[str | None, float | None, str | None]:
    if not isinstance(content, str):
        return None, None, "non_text_output"
    try:
        value = json.loads(content)
    except json.JSONDecodeError:
        return None, None, "invalid_json"
    if not isinstance(value, dict) or set(value) != {"label", "confidence"}:
        return None, None, "invalid_schema"
    label = value.get("label")
    confidence = value.get("confidence")
    if label not in CANONICAL_LABELS:
        return None, None, "invalid_label"
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        return None, None, "invalid_confidence"
    return label, float(confidence), None


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(len(ordered) * fraction + 0.999999) - 1))
    return ordered[index]


def aggregate(cases: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = [case["latency_seconds"] for case in cases]
    correct = sum(case["correct"] for case in cases)
    confusion: dict[str, Counter[str]] = defaultdict(Counter)
    for case in cases:
        confusion[case["expected"]][case["actual"] or f"ERROR:{case['error']}"] += 1
    return {
        "cases": len(cases),
        "correct": correct,
        "accuracy": correct / len(cases) if cases else 0.0,
        "errors": dict(Counter(case["error"] for case in cases if case["error"])),
        "input_tokens": sum(case["input_tokens"] for case in cases),
        "output_tokens": sum(case["output_tokens"] for case in cases),
        "total_tokens": sum(case["total_tokens"] for case in cases),
        "estimated_model_cost_usd": 0.0,
        "latency_seconds": {
            "total": sum(latencies),
            "mean": statistics.fmean(latencies) if latencies else 0.0,
            "p95": percentile(latencies, 0.95),
        },
        "confusion": {expected: dict(actuals) for expected, actuals in sorted(confusion.items())},
    }


def main() -> int:
    args = parse_args()
    if args.output.exists():
        raise SystemExit(f"output already exists: {args.output}")
    os.environ["PLAND_MODEL"] = args.model
    os.environ["PLAND_SEED"] = str(args.seed)
    module = load_agent(args.agent)
    sop = sop_snapshot(args.agent)
    system_prompt, invariants = frozen_invariants(args.agent, args.evals)

    with args.evals.open(encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row.get("split") == args.split]
    if not rows:
        raise SystemExit(f"no eval rows for split: {args.split}")

    cases = []
    for row in rows:
        datasource = row["input"].removeprefix("documents/")
        request = f"Classify approved datasource {datasource}."
        started = time.perf_counter()
        try:
            result = module.invoke_workflow(request)
            latency = time.perf_counter() - started
            trace = [serialize_message(message) for message in result["messages"]]
            final = trace[-1]["content"] if trace else None
            actual, confidence, error = parse_prediction(final)
        except Exception as exception:  # Preserve case-level infrastructure evidence.
            latency = time.perf_counter() - started
            trace = []
            actual, confidence = None, None
            error = f"infrastructure:{type(exception).__name__}:{exception}"

        usage = [message.get("usage") or {} for message in trace]
        input_tokens = sum(item.get("input_tokens", 0) or 0 for item in usage)
        output_tokens = sum(item.get("output_tokens", 0) or 0 for item in usage)
        total_tokens = sum(item.get("total_tokens", 0) or 0 for item in usage)
        skill_loaded = any(
            call.get("name") == "read_file"
            and call.get("args", {}).get("file_path") == "/skills/document-classification/SKILL.md"
            for message in trace for call in (message.get("tool_calls") or [])
        )
        datasource_read = any(
            call.get("name") in {"read_datasource", "analyze_datasource", "compact_datasource"}
            for message in trace for call in (message.get("tool_calls") or [])
        )
        if error is None and not skill_loaded:
            error = "skill_not_loaded"
        if error is None and not datasource_read:
            error = "datasource_not_read"
        cases.append({
            "id": row.get("id"),
            "split": args.split,
            "input": row["input"],
            "expected": row["output"],
            "actual": actual,
            "confidence": confidence,
            "correct": error is None and actual == row["output"],
            "error": error,
            "skill_loaded": skill_loaded,
            "datasource_read": datasource_read,
            "latency_seconds": latency,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "trace": trace,
        })
        print(json.dumps({key: cases[-1][key] for key in ("id", "expected", "actual", "correct", "error", "latency_seconds")}))

    payload = {
        "schema_version": 2,
        "created_at": datetime.now(UTC).isoformat(),
        "agent": args.agent.as_posix(),
        "evals": args.evals.as_posix(),
        "evals_sha256": hashlib.sha256(args.evals.read_bytes()).hexdigest(),
        "split": args.split,
        "model": args.model,
        "model_digest": ollama_digest(args.model),
        "seed": args.seed,
        "system_prompt": system_prompt,
        "invariants": invariants,
        "sop": sop,
        "summary": aggregate(cases),
        "cases": cases,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
