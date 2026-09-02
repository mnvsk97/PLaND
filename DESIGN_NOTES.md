# Path to Least Non-Determinism

## Objective

Transform an Agent Skill into the least non-deterministic hybrid workflow supported by evaluation evidence. Code steps bypass unnecessary model reasoning while natural-language steps preserve semantic flexibility.

The skill is the unit of capability, the SOP step is the unit of analysis, and the script is the unit of compilation.

## Skill representation

Every workflow step has exactly one representation:

1. A single English instruction for semantic or context-dependent judgment.
2. A relative reference to a focused supporting file; use another skill only for an independently discoverable capability.
3. An explicit command that runs a Python or Bash script for mechanical, stable, testable behavior.

The root `SKILL.md` orchestrates these steps. `scripts/`, `references/`, and `assets/` follow the Agent Skills specification conventions. `pyproject.toml` and `tests/` are project extensions for reproducible dependencies and executable-step verification.

## Dependency and network assumptions

- Python libraries are declared in `pyproject.toml`.
- Prefer maintained open-source libraries that run locally.
- Do not introduce a new paid product or metered service without authorization.
- Do not hide an LLM call inside a step classified as deterministic.
- Scripts may call explicitly permitted services, including APIs inside a VPC.
- Network destinations are governed by project policy rather than universally disabled.
- Credentials are injected by the runtime and are never stored in the skill.
- Total cost includes compute, storage, and service calls, not only model tokens.

## Agent generation and evolution loop

### Inputs

- requirements;
- datasource files;
- an optional existing skill;
- labeled examples with `input`, `output`, and `reasoning` columns;
- a fixed runtime model;
- a target validation accuracy and optimization guardrails.

The `reasoning` column is reference rationale. The runtime agent receives the row input and permitted datasource access, but never that row's expected output or reasoning.

### Baseline generation

Codex acts as the builder and optimizer. It inspects the requirements and data sources and generates a DeepAgent project:

```python
agent = create_deep_agent(
    model=MODEL,
    tools=[my_custom_tool],
    system_prompt=SYSTEM_PROMPT,
    skills=["./skills/<workflow-name>/"],
)
```

The runtime model stays fixed so improvements can be attributed to changes in the system prompt, SOP, skills, or tools.

### Evaluation

For each example:

1. Run the generated agent from an isolated initial state.
2. Store the input identifier, output, complete trace, errors, latency, token usage, and estimated cost.
3. Compare the actual output with independently held expected output using a task-appropriate scorer.
4. Aggregate accuracy and operational metrics.

Use task-appropriate metrics: exact accuracy or F1 for classification, field-level scores for extraction, and final-state verification for workflows. Use an LLM judge only for semantic properties that deterministic checks cannot settle.

### Evolution

If validation accuracy is below the target, Codex receives the development traces, outputs, expected outputs, reference reasoning, scorer feedback, and aggregate metrics. It clusters failures and proposes a bounded change.

Allowed changes:

- system prompt or `instructions.md`;
- `SOP.md`;
- skills and references;
- tools and deterministic scripts;
- `pyproject.toml` for approved dependencies.

Fixed during an experiment:

- runtime model;
- evaluation truth and scoring boundary;
- held-out examples;
- target accuracy;
- execution permissions and environment policy.

Evaluate one candidate against the same datasource snapshot, model, environment, timeout, scorer, and trial policy. Accept it only when it satisfies the accuracy guardrail and configured cost, latency, dependency, network, and security policies. Preserve evidence for accepted and rejected candidates.

### Data splits

- Development examples drive failure analysis and candidate generation.
- Validation examples select candidates and determine successful stopping.
- The final held-out set is used once for final reporting.

Do not repeatedly evolve against the held-out set.

### Stopping conditions

Success:

```text
validation_accuracy >= target_accuracy
```

Safety stops:

- maximum iterations;
- maximum optimization cost or elapsed time;
- no validation improvement for a configured number of iterations;
- repeated infrastructure failure;
- user interruption.

## Before and after

Before evolution, `SOP.md` is primarily a series of natural-language steps. After evolution, it is a hybrid of English instructions, focused references, and executable commands.

Compare both versions under identical conditions using:

- held-out task quality;
- average and percentile latency;
- input, output, and total tokens;
- average and total cost;
- error rate and run-to-run variance;
- number of model-mediated and executable steps;
- compilation cost and break-even execution count.

The system is not intended to eliminate natural language. It follows the path to least non-determinism by replacing only the instructions that evaluation evidence shows can be safely expressed as executable behavior.
