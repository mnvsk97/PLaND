#!/usr/bin/env python3
"""Run the prespecified PLaND text-classification variance study."""

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
SEEDS = (20260903, 20260904, 20260905)
STUDY = "variance-study-20260903"
DATASETS = {
    "ledgar": ("ledgar-text-classification", "test"),
    "cfpb": ("cfpb-text-classification", "validation"),
    "spamassassin": ("spamassassin-email-classification", "validation"),
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
    if sha256(HARNESS) != "26ab4ca8103f76e2e0380999feb1fdf52a7ce81c213b96f98ce92fe24c10f672":
        raise SystemExit("frozen run_experiment.py hash changed")
    wrong = {key: (os.environ.get(key), value) for key, value in REQUIRED_ENV.items()
             if os.environ.get(key) != value}
    if wrong:
        raise SystemExit(f"required Ollama environment mismatch: {wrong}")
    tags = json.loads(capture(["curl", "-fsS", "http://127.0.0.1:11434/api/tags"]))
    model = next((item for item in tags["models"] if item.get("name") == MODEL), None)
    if not model or model.get("digest") != MODEL_DIGEST:
        raise SystemExit("required qwen3:14b digest is unavailable")

    frozen = {}
    for short, (experiment_name, split) in DATASETS.items():
        experiment = ROOT / "experiments" / experiment_name
        source = experiment / "results" / f"confirmatory-{split}-nl.json"
        prior = json.loads(source.read_text(encoding="utf-8"))
        dataset = dataset_root / short
        observed = {
            "evals_sha256": sha256(dataset / "evals.csv"),
            "selection_sha256": sha256(dataset / "selection.json"),
        }
        expected = {key: prior["invariants"][key] for key in observed}
        if observed != expected:
            raise SystemExit(f"{short} dataset hashes differ from frozen evidence")
        frozen[short] = {
            "dataset_path": str(dataset.resolve()),
            "split": split,
            "dataset_hashes": observed,
            "system_prompt_sha256": sha256(experiment / "system-prompt.md"),
            "nl_sop_sha256": sha256(experiment / "nl/SKILL.md"),
            "hybrid_sop_sha256": sha256(experiment / "hybrid/SKILL.md"),
            "classifier_sha256": sha256(experiment / "hybrid/classify.py"),
        }
    return {
        "created_at": now(),
        "git_head": capture(["git", "-C", str(ROOT), "rev-parse", "HEAD"]),
        "git_status_before": capture(["git", "-C", str(ROOT), "status", "--short"]),
        "model": MODEL,
        "model_digest": MODEL_DIGEST,
        "ollama_version": capture(["ollama", "--version"]),
        "ollama_ps": capture(["ollama", "ps"]),
        "runtime": {
            "temperature": 0, "think": False, "stream": False,
            "num_ctx": 4096, "num_predict": 128, "keep_alive": -1,
            "workers": 2, **{key.lower(): value for key, value in REQUIRED_ENV.items()},
        },
        "seeds": list(SEEDS),
        "order": {str(SEEDS[0]): ["nl", "hybrid"], str(SEEDS[1]): ["hybrid", "nl"],
                  str(SEEDS[2]): ["nl", "hybrid"]},
        "frozen_artifacts": frozen,
        "harness_sha256": sha256(HARNESS),
        "comparison_sha256": sha256(COMPARE),
    }


def run_logged(command: list[str], log: Path, ledger: Path, label: str) -> None:
    state = json.loads(ledger.read_text(encoding="utf-8")) if ledger.exists() else {"runs": []}
    for prior in state["runs"]:
        if prior.get("label") == label and prior.get("status") == "running":
            prior.update({"status": "interrupted", "interruption_observed_at": now()})
            prior_log = log
            if prior_log.exists():
                prior["log_sha256_at_interruption"] = sha256(prior_log)
            partial = Path(next(command[index + 1] for index, value in enumerate(command[:-1])
                                if value == "--output")).with_suffix(".json.partial.json")
            if partial.exists():
                prior["checkpoint_cases_at_interruption"] = len(
                    json.loads(partial.read_text(encoding="utf-8")).get("cases", [])
                )
    if log.exists():
        number = 1
        while log.with_name(f"{log.stem}.resume-{number}{log.suffix}").exists():
            number += 1
        log = log.with_name(f"{log.stem}.resume-{number}{log.suffix}")
    entry = {"label": label, "command": shlex.join(command), "started_at": now(), "status": "running",
             "log": log.name}
    state["runs"].append(entry)
    atomic_json(ledger, state)
    print(f"START {label} {entry['started_at']}", flush=True)
    with log.open("x", encoding="utf-8") as handle:
        result = subprocess.run(command, cwd=ROOT, text=True, stdout=handle, stderr=subprocess.STDOUT)
    entry.update({"finished_at": now(), "exit_code": result.returncode,
                  "log_sha256": sha256(log), "status": "complete" if result.returncode == 0 else "failed"})
    atomic_json(ledger, state)
    print(f"FINISH {label} exit={result.returncode} {entry['finished_at']}", flush=True)
    if result.returncode:
        raise SystemExit(f"run failed: {label}; see {log}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", required=True, type=Path)
    parser.add_argument(
        "--output-root",
        type=Path,
        help=(
            "write a fresh mirror of experiment result directories under this root; "
            "the default preserves the original committed result locations"
        ),
    )
    args = parser.parse_args()
    metadata = preflight(args.dataset_root)
    reproduction_root = args.output_root.resolve() if args.output_root else None
    central = reproduction_root / "variance-study" if reproduction_root else ROOT / "experiments/variance-study"
    preflight_path = central / "preflight.json"
    if not preflight_path.exists():
        atomic_json(preflight_path, metadata)
    else:
        print(f"PRESERVE existing preflight evidence: {preflight_path}", flush=True)

    # Retain the model before timed work begins.
    subprocess.run(["curl", "-fsS", "http://127.0.0.1:11434/api/generate", "-H",
                    "Content-Type: application/json", "-d",
                    json.dumps({"model": MODEL, "keep_alive": -1, "options": {"num_ctx": 4096}})],
                   check=True, stdout=subprocess.DEVNULL)

    for seed in SEEDS:
        order = ("hybrid", "nl") if seed == SEEDS[1] else ("nl", "hybrid")
        for short, (experiment_name, split) in DATASETS.items():
            experiment = ROOT / "experiments" / experiment_name
            output_dir = (
                reproduction_root / experiment_name / "results" / STUDY
                if reproduction_root
                else experiment / "results" / STUDY
            )
            output_dir.mkdir(parents=True, exist_ok=True)
            ledger = output_dir / "run-ledger.json"
            dataset = args.dataset_root / short
            for variant in order:
                output = output_dir / f"seed-{seed}-{variant}.json"
                if output.exists():
                    print(f"SKIP complete {short} seed={seed} {variant}", flush=True)
                    continue
                command = [sys.executable, str(HARNESS), "--dataset", str(dataset), "--split", split,
                           "--system-prompt", str(experiment / "system-prompt.md"),
                           "--sop", str(experiment / variant / "SKILL.md"), "--model", MODEL,
                           "--seed", str(seed), "--workers", "2", "--num-ctx", "4096",
                           "--num-predict", "128", "--keep-alive", "-1", "--checkpoint-every", "10",
                           "--resume", "--output", str(output)]
                if variant == "hybrid":
                    command.extend(["--classifier", str(experiment / "hybrid/classify.py")])
                run_logged(command, output_dir / f"seed-{seed}-{variant}.log", ledger,
                           f"{short}:{split}:seed-{seed}:{variant}")
            comparison = output_dir / f"seed-{seed}-comparison.json"
            if not comparison.exists():
                command = [sys.executable, str(COMPARE), "--nl", str(output_dir / f"seed-{seed}-nl.json"),
                           "--hybrid", str(output_dir / f"seed-{seed}-hybrid.json"),
                           "--bootstrap-samples", "5000", "--bootstrap-seed", str(seed),
                           "--minimum-accuracy", "0.80", "--noninferiority-margin", "0.02",
                           "--minimum-token-reduction", "0.05", "--output", str(comparison)]
                run_logged(command, output_dir / f"seed-{seed}-comparison.log", ledger,
                           f"{short}:{split}:seed-{seed}:comparison")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
