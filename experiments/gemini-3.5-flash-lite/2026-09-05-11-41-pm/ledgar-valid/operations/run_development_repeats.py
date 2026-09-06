#!/usr/bin/env python3
"""Run or safely resume the three frozen LEDGAR development repeat pairs."""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
CONTROLLER = ROOT / ".codex/skills/pland-data-collection/scripts/run_collection.py"
RUNNER = ROOT / "experiments/collection/scripts/run_experiment.py"
RUN_DIR = ROOT / "experiments/gemini-3.5-flash-lite/2026-09-05-11-41-pm/ledgar-valid"
RESULTS = ROOT / "experiments/gemini-3.5-flash-lite/2026-09-05-11-41-pm/ledgar/results"
DATASET = ROOT / "tmp/gemini-3.5-flash-lite/2026-09-05-11-41-pm/datasets/ledgar-valid"
BASELINE = RUN_DIR / "packages/baseline-01"
CANDIDATE = RUN_DIR / "packages/candidate-02"
PYTHON = ROOT / "reproduce/.venv/bin/python"


def controller_command(name: str, output: Path, command: list[str], package: Path) -> None:
    argv = [str(PYTHON), str(CONTROLLER), "run-command", "--run-dir", str(RUN_DIR),
            "--stage", "candidate-development", "--name", name,
            "--input", str(DATASET), "--input", str(BASELINE), "--input", str(package),
            "--input", str(RUNNER),
            "--input", str(ROOT / "experiments/collection/scripts/hosted_execution.py"),
            "--input", str(ROOT / "experiments/collection/scripts/deepagent_execution.py"),
            "--input", str(ROOT / "reproduce/uv.lock"), "--output", str(output), "--", *command]
    subprocess.run(argv, cwd=ROOT, check=True)


def run(seed: int, arm: str) -> None:
    package = BASELINE if arm == "baseline" else CANDIDATE
    name = f"development-repeat-{seed}-{arm}"
    preflight = RESULTS / f"valid-{name}-preflight.json"
    output = RESULTS / f"valid-{name}.json"
    common = [str(PYTHON), str(RUNNER), "--dataset", str(DATASET), "--split", "development",
              "--system-prompt", str(BASELINE / "instructions.md"),
              "--sop", str(package / "skills/ledgar-classification/SKILL.md"),
              "--max-completion-tokens", "1024", "--request-timeout", "300", "--seed", str(seed),
              "--experiment-id", "gemini-3.5-flash-lite-2026-09-05-11-41-pm-ledgar-valid",
              "--candidate-id", "baseline" if arm == "baseline" else "candidate-02",
              "--attempt", "1" if arm == "baseline" else "2", "--workers", "8"]
    if arm == "hybrid":
        common.extend(["--classifier", str(CANDIDATE / "classify.py"),
                       "--baseline-sop", str(BASELINE / "skills/ledgar-classification/SKILL.md"),
                       "--command-step-id", "S03"])
    controller_command(name + "-preflight", preflight,
                       [*common, "--run-id", name + "-preflight", "--preflight-only", "--output", str(preflight)], package)
    actual = [*common, "--run-id", name, "--checkpoint-every", "10"]
    if output.with_suffix(output.suffix + ".partial.json").exists():
        actual.append("--resume")
    actual.extend(["--output", str(output)])
    controller_command(name, output, actual, package)


def main() -> int:
    for seed, arm in ((20260903, "baseline"), (20260903, "hybrid"),
                      (20260904, "hybrid"), (20260904, "baseline"),
                      (20260905, "baseline"), (20260905, "hybrid")):
        run(seed, arm)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
