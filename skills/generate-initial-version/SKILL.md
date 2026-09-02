---
name: generate-initial-version
description: Generate the first runnable LangChain DeepAgent from requirements, datasource files, and optional generation guidance. Use when starting a PLaND workflow before evaluation or SOP evolution.
metadata:
  project: pland
  version: "0.1.0"
---

# Generate the initial version

Create a minimal DeepAgent with exactly one workflow-named SOP skill. Optimize the initial SOP for a short, ordered, deterministic list of necessary steps; do not invent Python or Bash replacements before evaluation evidence exists.

## Generate

Require a requirements file, datasource directory, workflow name, and output directory. Optional generation guidance may specify constraints that are not present in the requirements.

Resolve the script relative to this skill directory and run:

```bash
python3 scripts/generate.py \
  --workflow <workflow-name> \
  --requirements <requirements-file> \
  --sources <datasource-directory> \
  --output <agent-directory> \
  [--model-provider generic|ollama] \
  [--guidance <generation-guidance-file>]
```

Then read the requirements, datasource manifest, and guidance. Replace the generated SOP's initial ordered steps with the shortest sufficient workflow. Each step must state one observable action or decision. Keep semantic judgment in English; references and command steps are introduced only when they reduce context or bypass model reasoning without changing behavior.

## Generated contract

The project contains:

- `agent.py` using `create_deep_agent`;
- `instructions.md` for compact always-on behavior;
- `skills/<workflow-name>/SKILL.md` as the only agent skill;
- `tools/datasources.py` as a local deterministic tool;
- `data/manifest.json` with source paths and hashes;
- `pyproject.toml` with open-source runtime dependencies.

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
