#!/usr/bin/env python3
"""Run or safely resume amended SpamAssassin selection/final repeats."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
PYTHON = ROOT / "reproduce/.venv/bin/python"
CONTROLLER = ROOT / ".codex/skills/pland-data-collection/scripts/run_collection.py"
RUNNER = ROOT / "experiments/collection/scripts/run_experiment.py"
RUN_DIR = ROOT / "experiments/gemini-3.5-flash-lite/2026-09-06-12-59-am/spamassassin"
RESULTS = RUN_DIR / "results"
DATASET = ROOT / "tmp/gemini-3.5-flash-lite/2026-09-06-12-59-am/datasets/spamassassin"
BASELINE = RUN_DIR / "packages/baseline-01"
CANDIDATE = RUN_DIR / "packages/candidate-01"


def controlled(stage: str, name: str, output: Path, command: list[str], package: Path) -> None:
    argv = [str(PYTHON), str(CONTROLLER), "run-command", "--run-dir", str(RUN_DIR),
            "--stage", stage, "--name", name,
            "--input", str(DATASET), "--input", str(BASELINE), "--input", str(package),
            "--input", str(RUNNER),
            "--input", str(ROOT / "experiments/collection/scripts/hosted_execution.py"),
            "--input", str(ROOT / "experiments/collection/scripts/deepagent_execution.py"),
            "--input", str(ROOT / "reproduce/uv.lock"), "--output", str(output), "--", *command]
    subprocess.run(argv, cwd=ROOT, check=True)


def run(stage: str, split: str, prefix: str, seed: int, arm: str) -> None:
    package = BASELINE if arm == "baseline" else CANDIDATE
    name = f"{prefix}-repeat-{seed}-{arm}"
    preflight = RESULTS / f"{name}-preflight.json"
    output = RESULTS / f"{name}.json"
    common = [str(PYTHON), str(RUNNER), "--dataset", str(DATASET), "--split", split,
              "--system-prompt", str(BASELINE / "instructions.md"),
              "--sop", str(package / "skills/spamassassin-classification/SKILL.md"),
              "--max-completion-tokens", "1024", "--request-timeout", "300", "--seed", str(seed),
              "--experiment-id", "gemini-3.5-flash-lite-2026-09-05-11-41-pm-amendment-01-spamassassin",
              "--candidate-id", "baseline" if arm == "baseline" else "candidate-01",
              "--attempt", "1", "--workers", "8"]
    if arm == "hybrid":
        common.extend(["--classifier", str(CANDIDATE / "classify.py"),
                       "--baseline-sop", str(BASELINE / "skills/spamassassin-classification/SKILL.md"),
                       "--command-step-id", "S03"])
    controlled(stage, name + "-preflight", preflight,
               [*common, "--run-id", name + "-preflight", "--preflight-only", "--output", str(preflight)], package)
    actual = [*common, "--run-id", name, "--checkpoint-every", "10"]
    if output.with_suffix(output.suffix + ".partial.json").exists():
        actual.append("--resume")
    actual.extend(["--output", str(output)])
    controlled(stage, name, output, actual, package)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--controller-stage", required=True, choices=("selection", "final-test"))
    parser.add_argument("--split", required=True, choices=("validation", "test"))
    parser.add_argument("--prefix", required=True, choices=("selection", "final-test"))
    args = parser.parse_args()
    for seed, arm in ((20260903, "baseline"), (20260903, "hybrid"),
                      (20260904, "hybrid"), (20260904, "baseline"),
                      (20260905, "baseline"), (20260905, "hybrid")):
        run(args.controller_stage, args.split, args.prefix, seed, arm)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
