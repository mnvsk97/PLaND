# PLaND: Path to Least Non-Determinism

PLaND uses two Agent Skills.

## 1. `generate-initial-version`

Inputs:

- workflow requirements;
- datasource files;
- optional guidance about initial generation.

Output: a runnable LangChain DeepAgent skeleton containing one workflow-named SOP skill.

```python
agent = create_deep_agent(
    model=MODEL,
    tools=[my_custom_tool],
    system_prompt=SYSTEM_PROMPT,
    skills=["./skills/"],
)
```

The initial project contains `agent.py`, `instructions.md`, `pyproject.toml`, a datasource manifest and tool, and exactly one `skills/<workflow>/SKILL.md`. The SOP begins as the shortest sufficient ordered list of natural-language actions and decisions. The generator does not create scripts, additional skills, subagents, memory, or graphs without an initial requirement for them.

## 2. `pland-evolver`

Inputs:

- the generated agent;
- labeled evals with `input`, `output`, and `reasoning`;
- a configured runner;
- a target validation accuracy and resource limits.

For each eval, run the agent from isolated state and store its output, complete trace, latency, tokens, cost, and errors. Score actual output against expected output. The runtime agent never receives that row's expected output or reasoning.

Use development traces and scorer feedback to propose one bounded change inside the workflow SOP package. Allowed changes are `SKILL.md`, its directly referenced instruction files, tools and Python/Bash scripts directly invoked by the SOP, and approved dependencies required by those scripts. Generate the system prompt once and freeze it after baseline measurement. Keep the model, system prompt, agent harness, evaluation truth, scorer, datasource snapshot, seed, held-out set, target, and execution permissions fixed.

Each SOP step has one representation:

1. a direct English instruction for semantic judgment;
2. a one-level relative reference for substantial supporting procedure;
3. an explicit Python or Bash command for mechanical, stable, testable behavior.

One deterministic step initially maps to one focused script. Code steps bypass unnecessary model reasoning while English steps preserve semantic flexibility. Never hide an LLM call inside a deterministic command.

Treat target accuracy as a quality floor. Accept a candidate only when validation evidence stays above that floor, improves the configured primary expense objective, and satisfies cost, latency, dependency, network, and security guardrails. Accuracy alone does not stop optimization. Enforce iteration, cost, time, and no-improvement limits, then run held-out data once for final reporting.

## Shared constraints

- Follow the Agent Skills specification and progressive disclosure.
- Keep `SKILL.md` short; move substantial conditional detail into focused references.
- Declare Python libraries in `pyproject.toml`.
- Prefer the standard library, then the smallest maintained open-source dependency set that materially improves correctness or resource use.
- Do not introduce a new paid product or metered service without explicit authorization.
- Treat a free SDK that requires a paid service, subscription, or usage plan as a paid dependency path.
- Optimize total expense across model tokens, wall-clock time, CPU, memory, storage, network, service charges, and repeated setup work.
- Bound loops, concurrency, retries, timeouts, input and output sizes, and temporary storage.
- Approved VPC and API calls are allowed under a fixed restricted network policy.
- Inject credentials at runtime and never store them in skills.
- Compare initial and evolved SOPs using held-out quality, cost, latency, token usage, variance, errors, and counts of English, reference, and command steps.

The skill is the unit of capability, the SOP step is the unit of analysis, and the script is the unit of compilation.
