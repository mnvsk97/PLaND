#!/usr/bin/env python3
"""Run three paired validation replications for frozen quality-first candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "experiments/text-classification/scripts/run_experiment.py"
COMPARE = ROOT / "experiments/text-classification/scripts/compare.py"
MODEL = "qwen3:14b"
MODEL_DIGEST = "bdbd181c33f2ed1b31c972991882db3cf4d192569092138a7d29e973cd9debe8"
SEEDS = (20260906, 20260907, 20260908)
STUDY = "quality-first-validation-20260903"
DATASETS = {
    "ledgar": "ledgar-text-classification",
    "cfpb": "cfpb-text-classification",
    "spamassassin": "spamassassin-email-classification",
}
REQUIRED_ENV = {
    "OLLAMA_FLASH_ATTENTION": "1",
    "OLLAMA_KV_CACHE_TYPE": "q8_0",
    "OLLAMA_NUM_PARALLEL": "2",
    "OLLAMA_MAX_LOADED_MODELS": "1",
    "OLLAMA_KEEP_ALIVE": "-1",
}


def now() -> str:
    return datetime.now(UTC).isoformat()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def capture(command: list[str]) -> str:
    return subprocess.run(command, check=True, text=True, capture_output=True).stdout.strip()


def preflight(dataset_root: Path) -> dict[str, object]:
    wrong = {
        key: (os.environ.get(key), expected)
        for key, expected in REQUIRED_ENV.items()
        if os.environ.get(key) != expected
    }
    if wrong:
        raise SystemExit(f"required Ollama environment mismatch: {wrong}")
    tags = json.loads(capture(["curl", "-fsS", "http://127.0.0.1:11434/api/tags"]))
    model = next((item for item in tags["models"] if item.get("name") == MODEL), None)
    if not model or model.get("digest") != MODEL_DIGEST:
        raise SystemExit("required qwen3:14b digest is unavailable")

    frozen = {}
    for short, experiment_name in DATASETS.items():
        experiment = ROOT / "experiments" / experiment_name
        dataset = dataset_root / short
        if not dataset.is_dir():
            raise SystemExit(f"missing prepared dataset: {dataset}")
        frozen[short] = {
            "dataset_path": str(dataset.resolve()),
            "evals_sha256": sha256(dataset / "evals.csv"),
            "selection_sha256": sha256(dataset / "selection.json"),
            "system_prompt_sha256": sha256(experiment / "system-prompt.md"),
            "natural_language_sop_sha256": sha256(experiment / "nl/SKILL.md"),
            "quality_first_sop_sha256": sha256(experiment / "quality-first/SKILL.md"),
            "quality_first_classifier_sha256": sha256(experiment / "quality-first/classify.py"),
        }
    return {
        "created_at": now(),
        "git_head": capture(["git", "-C", str(ROOT), "rev-parse", "HEAD"]),
        "git_status_before": capture(["git", "-C", str(ROOT), "status", "--short"]),
        "model": MODEL,
        "model_digest": MODEL_DIGEST,
        "runtime": {
            "temperature": 0,
            "think": False,
            "stream": False,
            "num_ctx": 4096,
            "num_predict": 128,
            "keep_alive": -1,
            "workers": 2,
            **{key.lower(): value for key, value in REQUIRED_ENV.items()},
        },
        "split": "validation",
        "seeds": list(SEEDS),
        "order": {
            str(SEEDS[0]): ["nl", "quality-first"],
            str(SEEDS[1]): ["quality-first", "nl"],
            str(SEEDS[2]): ["nl", "quality-first"],
        },
        "gates": {
            "minimum_accuracy": 0.8,
            "noninferiority_margin": 0.005,
            "minimum_accuracy_difference_lower_bound": -0.005,
            "require_no_accuracy_regression": True,
            "max_per_label_recall_drop": 0.02,
            "minimum_command_precision": 0.99,
            "minimum_token_reduction": 0.05,
        },
        "frozen_artifacts": frozen,
        "harness_sha256": sha256(HARNESS),
        "comparison_sha256": sha256(COMPARE),
    }


def run_logged(command: list[str], log: Path, ledger: Path, label: str) -> None:
    state = json.loads(ledger.read_text(encoding="utf-8")) if ledger.exists() else {"runs": []}
    if any(item.get("label") == label and item.get("status") == "complete" for item in state["runs"]):
        print(f"SKIP complete {label}", flush=True)
        return
    if log.exists():
        index = 1
        while log.with_name(f"{log.stem}.resume-{index}{log.suffix}").exists():
            index += 1
        log = log.with_name(f"{log.stem}.resume-{index}{log.suffix}")
    entry = {
        "label": label,
        "command": shlex.join(command),
        "started_at": now(),
        "status": "running",
        "log": log.name,
    }
    state["runs"].append(entry)
    atomic_json(ledger, state)
    print(f"START {label} {entry['started_at']}", flush=True)
    with log.open("x", encoding="utf-8") as handle:
        result = subprocess.run(command, cwd=ROOT, text=True, stdout=handle, stderr=subprocess.STDOUT)
    entry.update({
        "finished_at": now(),
        "exit_code": result.returncode,
        "status": "complete" if result.returncode == 0 else "failed",
        "log_sha256": sha256(log),
    })
    atomic_json(ledger, state)
    print(f"FINISH {label} exit={result.returncode} {entry['finished_at']}", flush=True)
    if result.returncode:
        raise SystemExit(f"run failed: {label}; see {log}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", required=True, type=Path)
    args = parser.parse_args()
    metadata = preflight(args.dataset_root)
    central = ROOT / "experiments/quality-first-replications"
    preflight_path = central / "preflight.json"
    if preflight_path.exists():
        prior = json.loads(preflight_path.read_text(encoding="utf-8"))
        frozen_fields = (
            "git_head", "model", "model_digest", "runtime", "split", "seeds",
            "order", "gates", "frozen_artifacts", "harness_sha256", "comparison_sha256",
        )
        changed = [field for field in frozen_fields if prior.get(field) != metadata.get(field)]
        if changed:
            raise SystemExit(f"preflight differs from frozen study fields: {changed}")
    else:
        if metadata["git_status_before"]:
            raise SystemExit("freeze the study in a clean Git commit before the first run")
        atomic_json(preflight_path, metadata)

    subprocess.run([
        "curl", "-fsS", "http://127.0.0.1:11434/api/generate",
        "-H", "Content-Type: application/json", "-d",
        json.dumps({"model": MODEL, "keep_alive": -1, "options": {"num_ctx": 4096}}),
    ], check=True, stdout=subprocess.DEVNULL)

    for seed in SEEDS:
        order = ("quality-first", "nl") if seed == SEEDS[1] else ("nl", "quality-first")
        for short, experiment_name in DATASETS.items():
            experiment = ROOT / "experiments" / experiment_name
            output_dir = experiment / "results" / STUDY
            output_dir.mkdir(parents=True, exist_ok=True)
            ledger = output_dir / "run-ledger.json"
            dataset = args.dataset_root / short
            for variant in order:
                output = output_dir / f"seed-{seed}-{variant}.json"
                if output.exists():
                    print(f"SKIP output {short}:{seed}:{variant}", flush=True)
                    continue
                sop_dir = "nl" if variant == "nl" else "quality-first"
                command = [
                    sys.executable, str(HARNESS), "--dataset", str(dataset),
                    "--split", "validation", "--system-prompt", str(experiment / "system-prompt.md"),
                    "--sop", str(experiment / sop_dir / "SKILL.md"), "--model", MODEL,
                    "--seed", str(seed), "--workers", "2", "--num-ctx", "4096",
                    "--num-predict", "128", "--keep-alive", "-1", "--checkpoint-every", "10",
                    "--resume", "--output", str(output),
                ]
                if variant == "quality-first":
                    command.extend(["--classifier", str(experiment / "quality-first/classify.py")])
                run_logged(command, output_dir / f"seed-{seed}-{variant}.log", ledger,
                           f"{short}:validation:seed-{seed}:{variant}")
            comparison = output_dir / f"seed-{seed}-comparison.json"
            if not comparison.exists():
                command = [
                    sys.executable, str(COMPARE),
                    "--nl", str(output_dir / f"seed-{seed}-nl.json"),
                    "--hybrid", str(output_dir / f"seed-{seed}-quality-first.json"),
                    "--bootstrap-samples", "5000", "--bootstrap-seed", str(seed),
                    "--minimum-accuracy", "0.80", "--noninferiority-margin", "0.005",
                    "--minimum-accuracy-difference-lower-bound", "-0.005",
                    "--minimum-token-reduction", "0.05", "--require-no-accuracy-regression",
                    "--max-per-label-recall-drop", "0.02", "--minimum-command-precision", "0.99",
                    "--output", str(comparison),
                ]
                run_logged(command, output_dir / f"seed-{seed}-comparison.log", ledger,
                           f"{short}:validation:seed-{seed}:comparison")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
