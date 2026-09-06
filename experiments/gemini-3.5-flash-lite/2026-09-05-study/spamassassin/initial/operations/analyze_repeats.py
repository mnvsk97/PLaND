#!/usr/bin/env python3
"""Analyze completed SpamAssassin repeat pairs under the collection controller."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
PYTHON = ROOT / "reproduce/.venv/bin/python"
CONTROLLER = ROOT / ".codex/skills/pland-data-collection/scripts/run_collection.py"
RUN_DIR = ROOT / "experiments/gemini-3.5-flash-lite/2026-09-05-11-41-pm/spamassassin"
RESULTS = RUN_DIR / "results"
SEEDS = (20260903, 20260904, 20260905)


def controlled(stage: str, name: str, inputs: list[Path], output: Path, command: list[str]) -> None:
    argv = [str(PYTHON), str(CONTROLLER), "run-command", "--run-dir", str(RUN_DIR),
            "--stage", stage, "--name", name]
    for path in inputs:
        argv.extend(["--input", str(path)])
    argv.extend(["--output", str(output), "--", *command])
    subprocess.run(argv, cwd=ROOT, check=True)


def development() -> None:
    compare = ROOT / "skills/pland-evolver/scripts/compare_variants.py"
    assess = ROOT / "skills/pland-evolver/scripts/assess_candidate.py"
    assessments = [RESULTS / "candidate-development-assessment-01.json"]
    for seed in SEEDS:
        baseline = RESULTS / f"development-repeat-{seed}-baseline.json"
        hybrid = RESULTS / f"development-repeat-{seed}-hybrid.json"
        comparison = RESULTS / f"development-repeat-{seed}-comparison.json"
        assessment = RESULTS / f"development-repeat-{seed}-assessment.json"
        controlled("candidate-development", f"compare-development-repeat-{seed}",
                   [baseline, hybrid, compare], comparison,
                   [str(PYTHON), str(compare), "--natural-language-run", str(baseline),
                    "--hybrid-run", str(hybrid), "--output", str(comparison)])
        controlled("candidate-development", f"assess-development-repeat-{seed}",
                   [baseline, hybrid, assess], assessment,
                   [str(PYTHON), str(assess), "--baseline-development", str(baseline),
                    "--candidate-development", str(hybrid), "--candidate", "candidate-01",
                    "--hypothesis", "Frozen repeat of SpamAssassin candidate-01 after development eligibility.",
                    "--iteration", "1", "--max-iterations", "10", "--target-quality", "0.8",
                    "--minimum-baseline-quality", "0.8", "--non-inferiority-margin", "0.02",
                    "--optimization-metric", "total_tokens", "--min-objective-improvement-ratio", "0.05",
                    "--require-hybrid-sop", "--max-validation-latency-ratio", "2.0",
                    "--output", str(assessment)])
        assessments.append(assessment)
    summarize = ROOT / "experiments/gemini-3.5-flash-lite/2026-09-05-11-41-pm/ledgar-valid/operations/summarize_development_gate.py"
    gate = RESULTS / "candidate-development-gate-01.json"
    command = [str(PYTHON), str(summarize)]
    for assessment in assessments:
        command.extend(["--assessment", str(assessment)])
    command.extend(["--output", str(gate)])
    controlled("candidate-development", "summarize-development-gate-01",
               [*assessments, summarize], gate, command)


def paired(stage: str, prefix: str) -> None:
    compare = ROOT / "experiments/collection/scripts/compare.py"
    comparisons = []
    for seed in SEEDS:
        baseline = RESULTS / f"{prefix}-repeat-{seed}-baseline.json"
        hybrid = RESULTS / f"{prefix}-repeat-{seed}-hybrid.json"
        comparison = RESULTS / f"{prefix}-repeat-{seed}-comparison.json"
        controlled(stage, f"compare-{prefix}-repeat-{seed}", [baseline, hybrid, compare], comparison,
                   [str(PYTHON), str(compare), "--nl", str(baseline), "--hybrid", str(hybrid),
                    "--bootstrap-samples", "5000", "--bootstrap-seed", "20260902",
                    "--noninferiority-margin", "0.02", "--minimum-token-reduction", "0.05",
                    "--minimum-accuracy", "0.8", "--output", str(comparison)])
        comparisons.append(comparison)
    if stage == "selection":
        summarize = ROOT / "experiments/gemini-3.5-flash-lite/2026-09-05-11-41-pm/ledgar-valid/operations/summarize_selection_gate.py"
        gate = RESULTS / "selection-gate.json"
        command = [str(PYTHON), str(summarize)]
        for comparison in comparisons:
            command.extend(["--comparison", str(comparison)])
        command.extend(["--output", str(gate)])
        controlled(stage, "summarize-selection-gate", [*comparisons, summarize], gate, command)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("development", "selection", "final-test"))
    args = parser.parse_args()
    if args.mode == "development":
        development()
    elif args.mode == "selection":
        paired("selection", "selection")
    else:
        paired("final-test", "final-test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
