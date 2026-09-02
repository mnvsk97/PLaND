#!/usr/bin/env python3
"""Initialize a deterministic-skill experiment without overwriting eval data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


TEMPLATES = {
    "SOP.md": """# SOP\n\n## Input contract\n\nTODO\n\n## Procedure\n\n1. TODO\n\n## Output contract\n\nTODO\n""",
    "EVOLVER.md": """# Evolution policy\n\n## Objective\n\nImprove accuracy while measuring cost and latency.\n\n## Production-data policy\n\nnone\n\n## Acceptance criteria\n\nTODO: define accuracy, cost, and latency thresholds.\n\n## Constraints\n\n- Evaluate every accepted change on the fixed evaluation set.\n- Prefer deterministic code when it preserves or improves accuracy.\n- Keep evidence for each accepted or rejected change.\n""",
    ".agent/runner.md": """# Runner adapter\n\n## Command\n\nTODO\n\n## Input mapping\n\nTODO\n\n## Output mapping\n\nTODO\n""",
    ".rule/README.md": """# Deterministic rules\n\nStore executable rules and generated helpers used by `SOP.md` here.\n""",
    "evals/README.md": """# Evaluation set\n\nDocument the immutable input format, expected outputs, scoring method, and train/eval boundary.\n""",
    ".gitignore": "runs/\n",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--task", required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    (root / "runs").mkdir(exist_ok=True)

    for relative, content in TEMPLATES.items():
        path = root / relative
        existed = path.exists()
        if existed and not args.force:
            print(f"kept {relative}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"{'updated' if existed else 'created'} {relative}")

    inventory = root / "INVENTORY.json"
    existed = inventory.exists()
    if not existed or args.force:
        payload = {
            "schema_version": 1,
            "task": args.task,
            "artifacts": {},
            "patterns": {},
        }
        inventory.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"{'updated' if existed else 'created'} INVENTORY.json")
    else:
        print("kept INVENTORY.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
