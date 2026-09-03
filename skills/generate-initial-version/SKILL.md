---
name: generate-initial-version
description: Generate the first runnable LangChain DeepAgent from requirements, datasource files, an eval CSV, and optional generation guidance. Use when starting a PLaND workflow before evaluation or SOP evolution.
metadata:
  project: pland
  version: "0.1.0"
---

# Generate the initial version

Create a minimal DeepAgent with exactly one workflow-named SOP skill. Optimize the initial SOP for a short, ordered, deterministic list of necessary steps; do not invent Python or Bash replacements before evaluation evidence exists.

## Generate

Require a requirements file, datasource directory, eval CSV, workflow name, and output directory. The CSV must contain `id`, `input`, and JSON-encoded `output` columns; `split`, `reasoning`, and `metadata` may also be present. Optional generation guidance may specify constraints that are not present in the requirements.

Resolve the script relative to this skill directory and run:

```bash
python3 scripts/generate.py \
  --workflow <workflow-name> \
  --requirements <requirements-file> \
  --sources <datasource-directory> \
  --evals <evals.csv> \
  --output <agent-directory> \
  [--model-provider generic|ollama] \
  [--guidance <generation-guidance-file>]
```

The user describes the task, success criteria, restrictions, approved data sources, and available tools in natural language and supplies examples when available. The generator translates that material into the initial agent and task-local evaluation files; the user should not need to author Python or Bash. Present the interpreted task contract for confirmation before baseline measurement, especially when success depends on state changes, action ordering, or semantic judgment. The local scaffold derives an initial SOP from the concise requirement, datasource file types, and eval output structure without treating classification as the default task. It never copies per-case IDs, answers, or reasoning into the agent. Then read the requirements, datasource manifest, eval profile, and guidance and shorten or clarify the generated steps when necessary. The baseline SOP must remain entirely English. Each numbered step has a stable identifier such as `[S01]`, states one observable action or decision, and ends with `<!-- pland:english -->`. Preserve an identifier when wording or representation later changes; never reuse a retired identifier. Only the evolver may introduce reference or command steps after trace evidence exists, and it must retain the original English instruction as the fallback.

## Generated contract

The project contains:

- `agent.py` using `create_deep_agent`;
- `instructions.md` for compact always-on behavior;
- `skills/<workflow-name>/SKILL.md` as the only agent skill;
- `tools/datasources.py` as a local deterministic tool;
- task-local runner and scorer files generated or adapted from the confirmed natural-language success contract;
- `data/manifest.json` with source paths and hashes;
- `data/eval-profile.json` with task structure but no case-level answers;
- `pyproject.toml` with open-source runtime dependencies.

`instructions.md` is the generated system prompt. Finalize it before baseline measurement; after the baseline begins, PLaND treats its exact content and SHA-256 hash as frozen experiment invariants.

The model is supplied through `PLAND_MODEL`. Use `--model-provider ollama` only when local Ollama is an explicit requirement; it adds the open-source `langchain-ollama` integration, deterministic local-model settings, disables the unnecessary default subagent, and hides filesystem tools outside the generated read-only workflow. Otherwise retain the provider-neutral default. Datasources remain in place unless the user explicitly requests copying. Do not store credentials.

Read [generation contract](references/generation-contract.md) when modifying the skeleton or deciding what belongs in the system prompt versus the SOP.

## Verify

Before handing off:

1. Validate the generated Agent Skill metadata.
2. Compile the Python files.
3. Confirm there is exactly one nested `SKILL.md` under `skills/`.
4. Confirm every imported non-standard library is declared in `pyproject.toml`.
5. Confirm `invoke_workflow` explicitly loads the one SOP before handling a request.
6. Confirm the agent can be imported once dependencies and `PLAND_MODEL` are available.
7. Confirm the generated runner and scorer implement the user-approved success contract without exposing expected answers to the runtime agent.
