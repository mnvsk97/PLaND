#!/usr/bin/env python3
"""Inject a PLaND SOP as a distinct skill context, then invoke tau2."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--sop", required=True, type=Path)
    known, remaining = parser.parse_known_args()
    base = Path(os.environ["PLAND_SYSTEM_PROMPT"]).read_text().strip()
    sop = known.sop.read_text().strip()
    compiled = known.sop.parent / "references" / "compiled-rules.md"
    if compiled.exists():
        sop += "\n\n" + compiled.read_text().strip()
    import tau2.agent.llm_agent as module
    module.AGENT_INSTRUCTION = base + "\n\n<skill>\n" + sop + "\n</skill>"
    # Keep evaluation local and deterministic. Retail's environment evaluator
    # derives the gold DB state by replaying the official reference actions.
    import tau2.runner.batch as batch
    from tau2.evaluator.evaluator import EvaluationType
    original_run_tasks = batch.run_tasks

    def run_tasks_env(*args, **kwargs):
        kwargs["evaluation_type"] = EvaluationType.ENV
        return original_run_tasks(*args, **kwargs)

    batch.run_tasks = run_tasks_env
    sys.argv = ["tau2", "run", *remaining]
    from tau2.cli import main as tau_main
    tau_main()


if __name__ == "__main__":
    main()
