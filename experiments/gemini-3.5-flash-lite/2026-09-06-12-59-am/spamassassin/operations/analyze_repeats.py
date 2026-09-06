#!/usr/bin/env python3
"""Analyze amended SpamAssassin paired repeats under the controller."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
PYTHON = ROOT / "reproduce/.venv/bin/python"
CONTROLLER = ROOT / ".codex/skills/pland-data-collection/scripts/run_collection.py"
RUN_DIR = ROOT / "experiments/gemini-3.5-flash-lite/2026-09-06-12-59-am/spamassassin"
RESULTS = RUN_DIR / "results"
SEEDS = (20260903, 20260904, 20260905)


def controlled(stage: str, name: str, inputs: list[Path], output: Path, command: list[str]) -> None:
    argv = [str(PYTHON), str(CONTROLLER), "run-command", "--run-dir", str(RUN_DIR),
            "--stage", stage, "--name", name]
    for path in inputs:
        argv.extend(["--input", str(path)])
    argv.extend(["--output", str(output), "--", *command])
    subprocess.run(argv, cwd=ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("selection", "final-test"))
    args = parser.parse_args()
    prefix = args.mode
    compare = ROOT / "experiments/collection/scripts/compare.py"
    comparisons = []
    for seed in SEEDS:
        baseline = RESULTS / f"{prefix}-repeat-{seed}-baseline.json"
        hybrid = RESULTS / f"{prefix}-repeat-{seed}-hybrid.json"
        comparison = RESULTS / f"{prefix}-repeat-{seed}-comparison.json"
        controlled(args.mode, f"compare-{prefix}-repeat-{seed}", [baseline, hybrid, compare], comparison,
                   [str(PYTHON), str(compare), "--nl", str(baseline), "--hybrid", str(hybrid),
                    "--bootstrap-samples", "5000", "--bootstrap-seed", "20260902",
                    "--noninferiority-margin", "0.02", "--minimum-token-reduction", "0.05",
                    "--minimum-accuracy", "0.8", "--output", str(comparison)])
        comparisons.append(comparison)
    if args.mode == "selection":
        summarize = ROOT / "experiments/gemini-3.5-flash-lite/2026-09-05-11-41-pm/ledgar-valid/operations/summarize_selection_gate.py"
        gate = RESULTS / "selection-gate.json"
        command = [str(PYTHON), str(summarize)]
        for comparison in comparisons:
            command.extend(["--comparison", str(comparison)])
        command.extend(["--output", str(gate)])
        controlled("selection", "summarize-selection-gate", [*comparisons, summarize], gate, command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
