#!/usr/bin/env python3
"""Record and gate resumable PLaND data-collection commands."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


STAGES = (
    "prepare",
    "baseline-development",
    "candidate-development",
    "selection",
    "final-test",
    "package-evidence",
    "paper-audit",
)
DECISIONS = {
    "baseline-development": {"ready", "refine", "nonviable"},
    "candidate-development": {"ready", "refine", "nonviable", "reject"},
    "selection": {"accept", "reject"},
}
EXPECTED_SPLITS = {"development": 500, "selection": 1000, "final_test": 500}


def now() -> str:
    return datetime.now(UTC).isoformat()


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def artifact(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.exists():
        raise ValueError(f"artifact does not exist: {path}")
    if resolved.is_file():
        return {
            "path": str(resolved),
            "kind": "file",
            "bytes": resolved.stat().st_size,
            "sha256": sha256(resolved),
        }
    # Python creates bytecode caches when it imports a frozen classifier.
    # These are interpreter artifacts, not mutable SOP/package source.
    files = sorted(item for item in resolved.rglob("*") if item.is_file()
                   and "__pycache__" not in item.relative_to(resolved).parts
                   and item.suffix not in {".pyc", ".pyo"})
    digest = hashlib.sha256()
    total = 0
    for item in files:
        relative = item.relative_to(resolved).as_posix()
        size = item.stat().st_size
        item_hash = sha256(item)
        digest.update(f"{relative}\0{size}\0{item_hash}\n".encode())
        total += size
    return {
        "path": str(resolved),
        "kind": "directory",
        "files": len(files),
        "bytes": total,
        "sha256": digest.hexdigest(),
    }


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def repository_root(start: Path) -> Path:
    result = subprocess.run(
        ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip()).resolve()


def git_value(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def validate_plan(plan: dict[str, Any], plan_path: Path, root: Path) -> Path:
    required = ("schema_version", "study_id", "protocol", "datasets", "splits",
                "model", "limits", "acceptance", "paper")
    missing = [key for key in required if key not in plan]
    if missing:
        raise ValueError("plan missing fields: " + ", ".join(missing))
    if plan["schema_version"] != 1 or not isinstance(plan["study_id"], str) or not plan["study_id"].strip():
        raise ValueError("plan requires schema_version 1 and a non-empty study_id")
    if not isinstance(plan["datasets"], list) or not plan["datasets"]:
        raise ValueError("plan datasets must be a non-empty list")
    if plan["splits"] != EXPECTED_SPLITS:
        raise ValueError(
            "fresh paper collection requires exactly 500 development, "
            "1000 selection, and 500 final_test cases"
        )
    model = plan["model"]
    if not isinstance(model, dict) or not model.get("name") or not model.get("digest"):
        raise ValueError("plan model requires name and digest")
    limits = plan["limits"]
    for key in ("baseline_attempts", "candidate_attempts"):
        if not isinstance(limits.get(key), int) or limits[key] < 1:
            raise ValueError(f"plan limits.{key} must be a positive integer")
    protocol = Path(plan["protocol"])
    if not protocol.is_absolute():
        protocol = root / protocol
    if not protocol.is_file():
        raise ValueError(f"protocol does not exist: {protocol}")
    paper_source = Path(plan["paper"].get("source", ""))
    if not paper_source.is_absolute():
        paper_source = root / paper_source
    if not paper_source.is_file():
        raise ValueError(f"paper source does not exist: {paper_source}")
    if root not in plan_path.resolve().parents:
        raise ValueError("plan must be stored inside the repository")
    return protocol.resolve()


def state_paths(run_dir: Path) -> tuple[Path, Path]:
    return run_dir / "collection-state.json", run_dir / "command-ledger.json"


def load_state(run_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    state_path, ledger_path = state_paths(run_dir)
    if not state_path.is_file() or not ledger_path.is_file():
        raise ValueError(f"collection is not initialized: {run_dir}")
    state, ledger = load_json(state_path), load_json(ledger_path)
    plan_path = Path(state["plan"]["path"])
    protocol_path = Path(state["protocol"]["path"])
    if sha256(plan_path) != state["plan"]["sha256"]:
        raise ValueError("frozen plan changed after collection initialization")
    if sha256(protocol_path) != state["protocol"]["sha256"]:
        raise ValueError("frozen protocol changed after collection initialization")
    hold = run_dir / "collection-hold.json"
    if hold.exists():
        state["safety_hold"] = artifact(hold)
    return state, ledger


def successful_events(ledger: dict[str, Any], stage: str) -> list[dict[str, Any]]:
    return [event for event in ledger["events"] if event["stage"] == stage and event["status"] == "complete"]


def latest_decision(state: dict[str, Any], stage: str) -> str | None:
    decisions = state["decisions"].get(stage, [])
    return decisions[-1]["value"] if decisions else None


def require_stage_access(
    state: dict[str, Any], ledger: dict[str, Any], stage: str, *, starting_command: bool = False
) -> None:
    if state.get("safety_hold"):
        raise ValueError("collection safety hold: inspect " + state["safety_hold"]["path"])
    if stage == "baseline-development" and state["stages"]["prepare"] != "complete":
        raise ValueError("prepare must be complete before baseline development")
    if stage == "candidate-development" and latest_decision(state, "baseline-development") != "ready":
        raise ValueError("baseline must be ready before candidate development")
    if stage == "candidate-development" and (state['decisions']['selection'] or successful_events(ledger, 'selection')):
        raise ValueError("candidate work is forbidden after selection opens")
    if stage == "candidate-development" and latest_decision(state, stage) in {'ready', 'reject', 'nonviable'}:
        raise ValueError("candidate development is already terminal or frozen")
    if stage == "selection" and latest_decision(state, "candidate-development") != "ready":
        raise ValueError("candidate must be ready before selection")
    if stage == "final-test" and latest_decision(state, "selection") != "accept":
        raise ValueError("selection must be accepted before final test")
    terminal = (
        latest_decision(state, "baseline-development") == "nonviable"
        or latest_decision(state, "candidate-development") in {"reject", "nonviable"}
        or latest_decision(state, "selection") == "reject"
        or state["stages"]["final-test"] == "complete"
    )
    if stage == "package-evidence" and not terminal:
        raise ValueError("evidence may be packaged only after a terminal study outcome")
    if stage == "paper-audit" and state["stages"]["package-evidence"] != "complete":
        raise ValueError("package-evidence must be complete before paper audit")
    if starting_command:
        limits = state["limits"]
        if stage == "baseline-development" and len(state["decisions"][stage]) >= limits["baseline_attempts"]:
            raise ValueError("baseline attempt limit reached")
        if stage == "candidate-development" and len(state["decisions"][stage]) >= limits["candidate_attempts"]:
            raise ValueError("candidate attempt limit reached")


def initialize(args: argparse.Namespace) -> int:
    plan_path = args.plan.resolve()
    root = repository_root(plan_path.parent)
    plan = load_json(plan_path)
    protocol = validate_plan(plan, plan_path, root)
    status = git_value(root, "status", "--short")
    if status and not args.allow_dirty:
        raise ValueError("Git tree is dirty; freeze the reviewed plan and code before paper data collection")
    run_dir = args.run_dir.resolve()
    if run_dir.exists():
        raise ValueError(f"run directory already exists: {run_dir}")
    run_dir.mkdir(parents=True)
    state = {
        "schema_version": 1,
        "study_id": plan["study_id"],
        "created_at": now(),
        "repository": str(root),
        "git_head": git_value(root, "rev-parse", "HEAD"),
        "git_status_at_init": status,
        "plan": artifact(plan_path),
        "protocol": artifact(protocol),
        "limits": plan["limits"],
        "stages": {stage: "pending" for stage in STAGES},
        "decisions": {stage: [] for stage in DECISIONS},
    }
    atomic_json(run_dir / "collection-state.json", state)
    atomic_json(run_dir / "command-ledger.json", {"schema_version": 1, "events": []})
    print(json.dumps({"status": "initialized", "study_id": plan["study_id"], "run_dir": str(run_dir)}))
    return 0


def run_command(args: argparse.Namespace) -> int:
    run_dir = args.run_dir.resolve()
    state, ledger = load_state(run_dir)
    if state.get("safety_hold"):
        require_stage_access(state, ledger, args.stage)
    completed = [event for event in successful_events(ledger, args.stage) if event["name"] == args.name]
    if completed:
        recorded = completed[-1]
        current = [artifact(Path(item["path"])) for item in recorded["outputs"]]
        if [item["sha256"] for item in current] != [item["sha256"] for item in recorded["outputs"]]:
            raise ValueError(f"completed command output changed: {args.name}")
        print(json.dumps({"status": "already_complete", "name": args.name}))
        return 0
    require_stage_access(state, ledger, args.stage, starting_command=True)
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise ValueError("run-command requires an argv command after --")
    cwd = args.cwd.resolve() if args.cwd else Path(state["repository"])
    inputs = [artifact(path) for path in args.input]
    attempt = 1 + sum(event["name"] == args.name for event in ledger["events"])
    log_root = run_dir / "logs"
    log_root.mkdir(exist_ok=True)
    safe_name = "".join(character if character.isalnum() or character in "-_" else "-" for character in args.name)
    stdout_path = log_root / f"{args.stage}-{safe_name}-attempt-{attempt}.stdout.log"
    stderr_path = log_root / f"{args.stage}-{safe_name}-attempt-{attempt}.stderr.log"
    event = {
        "name": args.name,
        "stage": args.stage,
        "attempt": attempt,
        "status": "running",
        "command": command,
        "cwd": str(cwd),
        "started_at": now(),
        "plan_sha256": state["plan"]["sha256"],
        "protocol_sha256": state["protocol"]["sha256"],
        "inputs": inputs,
        "declared_outputs": [str(path.resolve()) for path in args.output],
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
    }
    ledger["events"].append(event)
    atomic_json(run_dir / "command-ledger.json", ledger)
    with stdout_path.open("x", encoding="utf-8") as stdout, stderr_path.open("x", encoding="utf-8") as stderr:
        result = subprocess.run(command, cwd=cwd, stdout=stdout, stderr=stderr, text=True)
    event["finished_at"] = now()
    event["exit_code"] = result.returncode
    try:
        event["outputs"] = [artifact(path) for path in args.output] if result.returncode == 0 else []
        event["status"] = "complete" if result.returncode == 0 else "failed"
    except ValueError as error:
        event["status"] = "failed"
        event["output_error"] = str(error)
    atomic_json(run_dir / "command-ledger.json", ledger)
    print(json.dumps({"status": event["status"], "name": args.name, "exit_code": result.returncode}))
    return 0 if event["status"] == "complete" else 1


def decision(args: argparse.Namespace) -> int:
    run_dir = args.run_dir.resolve()
    state, ledger = load_state(run_dir)
    require_stage_access(state, ledger, args.stage)
    if args.value not in DECISIONS[args.stage]:
        raise ValueError(f"invalid {args.stage} decision: {args.value}")
    if not successful_events(ledger, args.stage):
        raise ValueError("a successful stage command is required before recording a decision")
    evidence = artifact(args.evidence)
    if args.stage in {'baseline-development', 'candidate-development'}:
        limit = state['limits']['baseline_attempts' if args.stage == 'baseline-development' else 'candidate_attempts']
        count = len(state['decisions'][args.stage]) + 1
        if count > limit or (args.value == 'refine' and count >= limit):
            raise ValueError('decision exceeds the approved attempt budget')
    entry = {"value": args.value, "recorded_at": now(), "evidence": evidence}
    state["decisions"][args.stage].append(entry)
    state["stages"][args.stage] = "complete" if args.value != "refine" else "in_progress"
    atomic_json(run_dir / "collection-state.json", state)
    print(json.dumps({"stage": args.stage, "decision": args.value}))
    return 0


def complete_stage(args: argparse.Namespace) -> int:
    if args.stage in DECISIONS:
        raise ValueError(f"use decision for stage {args.stage}")
    run_dir = args.run_dir.resolve()
    state, ledger = load_state(run_dir)
    require_stage_access(state, ledger, args.stage)
    if not successful_events(ledger, args.stage):
        raise ValueError("a successful stage command is required before completing a stage")
    state["stages"][args.stage] = "complete"
    atomic_json(run_dir / "collection-state.json", state)
    print(json.dumps({"stage": args.stage, "status": "complete"}))
    return 0


def create_manifest(args: argparse.Namespace) -> int:
    run_dir = args.run_dir.resolve()
    state, ledger = load_state(run_dir)
    require_stage_access(state, ledger, "package-evidence")
    if state["stages"]["package-evidence"] != "complete":
        raise ValueError("complete package-evidence before generating its manifest")
    files: dict[str, dict[str, Any]] = {}
    for item in (state["plan"], state["protocol"]):
        files[item["path"]] = artifact(Path(item["path"]))
    for amendment in state.get('amendments', []):
        for key in ['original_plan','original_protocol','amended_plan','amended_protocol','authorization']:
            item=amendment[key]
            assert artifact(Path(item['path']))['sha256']==item['sha256']
            files[item['path']]=item
    for path in (run_dir / "collection-state.json", run_dir / "command-ledger.json"):
        files[str(path.resolve())] = artifact(path)
    for event in ledger["events"]:
        for item in event.get("inputs", []) + event.get("outputs", []):
            files[item["path"]] = item
        for key in ("stdout", "stderr"):
            path = Path(event[key])
            files[str(path.resolve())] = artifact(path)
    for history in state["decisions"].values():
        for item in history:
            files[item["evidence"]["path"]] = item["evidence"]
    manifest = {
        "schema_version": 1,
        "study_id": state["study_id"],
        "created_at": now(),
        "plan_sha256": state["plan"]["sha256"],
        "protocol_sha256": state["protocol"]["sha256"],
        "git_head": state["git_head"],
        "artifacts": sorted(files.values(), key=lambda item: item["path"]),
    }
    destination = run_dir / "evidence-manifest.json"
    atomic_json(destination, manifest)
    export_dir = getattr(args, "export_dir", None)
    if export_dir is not None:
        export_dir = export_dir.resolve()
        if not export_dir.is_dir():
            raise ValueError("export directory must already contain the safe evidence package")
        for name in ("collection-state.json", "command-ledger.json", "evidence-manifest.json"):
            shutil.copy2(run_dir / name, export_dir / name)
        shutil.copytree(run_dir / "logs", export_dir / "logs", dirs_exist_ok=True)
        safe_files = []
        for path in sorted(export_dir.rglob("*")):
            if path.is_file() and path != export_dir / "manifest.json":
                item = artifact(path)
                safe_files.append({"path": path.relative_to(export_dir).as_posix(),
                                   "bytes": item["bytes"], "sha256": item["sha256"]})
        atomic_json(export_dir / "manifest.json", {
            "schema_version": 1, "study_id": state["study_id"],
            "plan_sha256": state["plan"]["sha256"], "files": safe_files,
        })
    print(json.dumps({"status": "manifested", "artifacts": len(files), "path": str(destination)}))
    return 0


def status(args: argparse.Namespace) -> int:
    state, ledger = load_state(args.run_dir.resolve())
    print(json.dumps({
        "study_id": state["study_id"],
        "git_head": state["git_head"],
        "plan_sha256": state["plan"]["sha256"],
        "stages": state["stages"],
        "decisions": {key: (value[-1]["value"] if value else None) for key, value in state["decisions"].items()},
        "commands": {"complete": len([e for e in ledger["events"] if e["status"] == "complete"]),
                     "failed": len([e for e in ledger["events"] if e["status"] == "failed"])},
    }, indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="action", required=True)
    init = sub.add_parser("init")
    init.add_argument("--plan", required=True, type=Path)
    init.add_argument("--run-dir", required=True, type=Path)
    init.add_argument("--allow-dirty", action="store_true")
    init.set_defaults(function=initialize)

    run = sub.add_parser("run-command")
    run.add_argument("--run-dir", required=True, type=Path)
    run.add_argument("--stage", required=True, choices=STAGES)
    run.add_argument("--name", required=True)
    run.add_argument("--cwd", type=Path)
    run.add_argument("--input", action="append", type=Path, default=[])
    run.add_argument("--output", action="append", type=Path, default=[])
    run.add_argument("command", nargs=argparse.REMAINDER)
    run.set_defaults(function=run_command)

    choose = sub.add_parser("decision")
    choose.add_argument("--run-dir", required=True, type=Path)
    choose.add_argument("--stage", required=True, choices=tuple(DECISIONS))
    choose.add_argument("--value", required=True)
    choose.add_argument("--evidence", required=True, type=Path)
    choose.set_defaults(function=decision)

    complete = sub.add_parser("complete-stage")
    complete.add_argument("--run-dir", required=True, type=Path)
    complete.add_argument("--stage", required=True, choices=STAGES)
    complete.set_defaults(function=complete_stage)

    manifest = sub.add_parser("manifest")
    manifest.add_argument("--run-dir", required=True, type=Path)
    manifest.add_argument("--export-dir", type=Path)
    manifest.set_defaults(function=create_manifest)

    show = sub.add_parser("status")
    show.add_argument("--run-dir", required=True, type=Path)
    show.set_defaults(function=status)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        return args.function(args)
    except (OSError, ValueError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    raise SystemExit(main())
