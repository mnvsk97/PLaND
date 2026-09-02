---
name: init
description: Initialize a deterministic-skill experiment from a task description, evaluation cases, and an optional existing agent or SOP. Use when starting or resetting the structure for a skill-evolution study.
---

# Initialize a deterministic-skill experiment

Create the smallest reproducible workspace needed to evolve an agent's prose workflow into deterministic instructions and code.

## Inputs

Collect or locate:

- the task and expected output contract;
- an evaluation set with inputs and expected outcomes or scoring criteria;
- the runner command or adapter for the target agent;
- an existing `SOP.md`, if one exists;
- optimization priorities for accuracy, cost, and latency;
- the production-data policy: `none` or `few`, including the exact approved examples when `few` is selected.

Do not use production runs or production data unless the user explicitly selects `few` and supplies or identifies the allowed examples.

## Initialize

Run:

```bash
python3 scripts/init_experiment.py --root <experiment-directory> --task <task-name>
```

Resolve `scripts/init_experiment.py` relative to this skill directory. Add `--force` only when the user explicitly asks to replace generated starter files; it never replaces evaluation data.

Then fill the generated files with known facts. Keep unknown runner details and scoring thresholds as explicit TODOs rather than inventing them.

## Result

The initialized experiment contains:

- `.agent/`: agent configuration and adapters;
- `.rule/`: deterministic rules and generated helpers;
- `SOP.md`: the current executable procedure;
- `EVOLVER.md`: evolution constraints and acceptance policy;
- `INVENTORY.json`: artifact and pattern registry;
- `evals/`: evaluation cases and scoring contract;
- `runs/`: ignored run outputs.

Finish by validating that the eval input format, expected output, runner command, and optimization priority are all explicit. Do not begin evolution when any of these would materially change how results are scored.
