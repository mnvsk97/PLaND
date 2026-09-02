---
name: path-to-least-non-determinism
description: Transform a natural-language Agent Skill into a hybrid workflow whose steps are English instructions, local file references, or executable commands. Use when reducing unnecessary model reasoning with verified Python or Bash steps while preserving semantic judgment.
compatibility: Requires Python 3.11+. Generated Python dependencies are declared in pyproject.toml.
metadata:
  project: deterministic-skills
  version: "0.1.0"
---

# Path to Least Non-Determinism

Produce the least non-deterministic hybrid skill supported by evaluation evidence. Code steps bypass unnecessary model reasoning; natural-language steps preserve semantic flexibility.

## Inputs

Require:

- a directory containing the task's data sources;
- a CSV with `input`, `output`, and `reasoning` columns; `id` is optional;
- a task name;
- an output directory for the generated project.

Treat `reasoning` as reference rationale, not guaranteed truth. Never expose `output` or `reasoning` to the runtime agent while evaluating that row.

## Initialize the project

Resolve scripts relative to this skill directory, then run:

```bash
python3 scripts/scaffold.py \
  --task <task-name> \
  --sources <datasource-directory> \
  --evals <evals.csv> \
  --output <generated-project-directory>
```

This validates the inputs, records hashes, copies the eval CSV, and creates an Agent Skills-compatible hybrid project. Source files are inventoried but not copied unless `--copy-sources` is supplied.

## Analyze the workflow

For each proposed SOP step, choose exactly one representation:

1. **Instruction** — retain English when the step requires semantic interpretation, contextual judgment, conflict resolution, or adaptation to novel inputs.
2. **Reference** — link a focused file under `references/` when instructions are too large for the root skill. Create another skill only when the procedure is independently discoverable and reusable.
3. **Command** — create one Python or Bash script when the step is mechanical, stable, testable, and meaningfully bypasses model reasoning.

Do not hide an LLM or agent call inside a command classified as deterministic.

Read [step contract](references/step-contract.md) before adding or changing steps. Read [dependency policy](references/dependency-policy.md) before editing a generated `pyproject.toml` or adding networked behavior.

## Compile a command step

For every command step:

- give the script one clear responsibility;
- use explicit arguments and structured output where practical;
- document exit codes and failure behavior;
- declare Python libraries in the generated project's `pyproject.toml`;
- add focused success, boundary, and failure checks;
- record the source instruction and evidence in `INVENTORY.json`;
- compare the complete hybrid skill against the baseline on development data;
- accept the replacement only when it satisfies the accuracy guardrail and the configured cost and latency policy.

Network access may be used for explicitly permitted endpoints, including services inside a VPC. Credentials must come from the runtime. Reject undeclared endpoints, hidden metered model calls, permission expansion, or new paid services that the user did not authorize.

## Evaluation boundary

Split examples into development, validation, and final held-out sets. Evolve on development data, select candidates using validation data, and reserve the held-out set for final evaluation. Do not report a step as compiled safely from unit checks alone; require end-to-end evidence.

The skill is the unit of capability, the SOP step is the unit of analysis, and the script is the unit of compilation.
