#!/usr/bin/env python3
"""Run and summarize the frozen tau-retail NL/hybrid PLaND comparison."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import resource
import shutil
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def subset_ids(evals: Path, counts: dict[str, int]) -> list[str]:
    selected: list[str] = []
    used = {key: 0 for key in counts}
    with evals.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            split = row["split"]
            if split in counts and used[split] < counts[split]:
                selected.append(json.loads(row["metadata"])["upstream_task_id"])
                used[split] += 1
    if used != counts:
        raise ValueError(f"insufficient cases: {used}")
    return selected


def sop_stats(path: Path) -> dict[str, int]:
    text = path.read_text()
    steps = [line for line in text.splitlines() if line[:1].isdigit()]
    return {
        "bytes": len(text.encode()), "tokens_estimated": (len(text) + 3) // 4,
        "steps": len(steps), "command_steps": sum("`python " in line or "`bash " in line for line in steps),
        "reference_steps": sum("](references/" in line for line in steps),
        "natural_language_steps": sum("`python " not in line and "`bash " not in line and "](references/" not in line for line in steps),
    }


def summarize(results: Path, wall: float, peak_before: int) -> dict:
    data = json.loads(results.read_text())
    sims = data["simulations"]
    rewards = [float((sim.get("reward_info") or {}).get("reward") or 0) for sim in sims]
    agent_tokens = sum(
        sum((msg.get("usage") or {}).values())
        for sim in sims for msg in sim.get("messages", []) if msg.get("role") == "assistant"
    )
    user_tokens = sum(
        sum((msg.get("usage") or {}).values())
        for sim in sims for msg in sim.get("messages", []) if msg.get("role") == "user"
    )
    tool_calls = sum(len(msg.get("tool_calls") or []) for sim in sims for msg in sim.get("messages", []))
    return {
        "cases": len(sims), "task_success": sum(x == 1 for x in rewards) / len(rewards),
        "final_state_correctness": sum(rewards) / len(rewards),
        "agent_tokens": agent_tokens, "user_tokens": user_tokens,
        "total_tokens": agent_tokens + user_tokens, "wall_seconds": wall,
        "mean_case_latency_seconds": sum(float(s.get("duration") or 0) for s in sims) / len(sims),
        "tool_calls": tool_calls, "estimated_api_cost_usd": 0,
        "peak_child_rss_delta_platform_units": max(0, resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss - peak_before),
        "termination_reasons": {reason: sum(s.get("termination_reason") == reason for s in sims) for reason in sorted({s.get("termination_reason") for s in sims})},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--tau-repo", required=True, type=Path)
    parser.add_argument("--candidate", choices=["nl", "hybrid", "both"], default="both")
    args = parser.parse_args()
    args.dataset = args.dataset.resolve()
    args.tau_repo = args.tau_repo.resolve()
    config = json.loads((ROOT / "config.json").read_text())
    if subprocess.check_output(["git", "-C", args.tau_repo, "rev-parse", "HEAD"], text=True).strip() != config["tau_revision"]:
        raise SystemExit("tau revision invariant failed")
    selection = json.loads((args.dataset / "selection.json").read_text())
    if selection["revision"] != config["tau_revision"] or selection["seed"] != config["dataset_seed"]:
        raise SystemExit("dataset invariant failed")
    ids = subset_ids(args.dataset / "evals.csv", config["paper_subset"])
    frozen = {
        "model": config["model"], "model_digest": config["ollama_digest"],
        "system_prompt_sha256": digest(ROOT / "system-prompt.txt"),
        "evals_sha256": digest(args.dataset / "evals.csv"),
        "selection_sha256": digest(args.dataset / "selection.json"),
        "policy_sha256": digest(args.dataset / "sources" / "policy.md"),
        "scorer": config["evaluation"], "seed": config["run_seed"],
        "permissions": config["network_permissions"], "task_ids": ids,
    }
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    (out / "invariants.json").write_text(json.dumps(frozen, indent=2) + "\n")
    candidates = ["nl", "hybrid"] if args.candidate == "both" else [args.candidate]
    if "hybrid" in candidates:
        subprocess.run([
            str(args.tau_repo / ".venv/bin/python"), str(ROOT / "sop/hybrid/scripts/compile_policy.py"),
            "--policy", str(args.dataset / "sources/policy.md"),
            "--output", str(ROOT / "sop/hybrid/references/compiled-rules.md")], check=True)
    for candidate in candidates:
        sop = ROOT / "sop" / candidate / "SKILL.md"
        save_name = f"pland-{candidate}"
        shutil.rmtree(args.tau_repo / "data/simulations" / save_name, ignore_errors=True)
        cmd = [str(args.tau_repo / ".venv/bin/python"), str(ROOT / "launch_tau.py"), "--sop", str(sop),
            "--domain", "retail", "--agent-llm", config["model"], "--user-llm", config["model"],
            "--agent-llm-args", json.dumps({"temperature":0,"api_base":"http://localhost:11434","extra_body":{"think":False},"num_predict":512}),
            "--user-llm-args", json.dumps({"temperature":0,"api_base":"http://localhost:11434","extra_body":{"think":False},"num_predict":256}),
            "--task-ids", *ids, "--num-trials", "1", "--max-concurrency", str(config["max_concurrency"]),
            "--max-steps", str(config["max_steps"]), "--timeout", str(config["timeout_seconds"]),
            "--max-retries", "0", "--seed", str(config["run_seed"]), "--save-to", save_name]
        env = {**os.environ, "PLAND_SYSTEM_PROMPT": str(ROOT / "system-prompt.txt")}
        peak = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        start = time.monotonic()
        completed = subprocess.run(cmd, cwd=args.tau_repo, env=env)
        wall = time.monotonic() - start
        if completed.returncode:
            raise SystemExit(completed.returncode)
        source = args.tau_repo / "data/simulations" / save_name / "results.json"
        shutil.copy2(source, out / f"{candidate}-traces.json")
        summary = summarize(source, wall, peak)
        summary["sop_sha256"] = digest(sop)
        summary["sop_representation"] = sop_stats(sop)
        summary["resource_snapshot"] = {
            "model_file_bytes": config["ollama_model_file_bytes"],
            "runtime_processor": config["ollama_runtime_processor"],
            "loaded_size_reported": config["ollama_loaded_size_reported"],
        }
        (out / f"{candidate}-metrics.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
