---
name: pland-evolver
description: Improve a generated DeepAgent by evaluating its single SOP skill and replacing eligible English steps with verified Python or Bash commands. Use after generate-initial-version when labeled evals and an accuracy target are available.
metadata:
  project: pland
  version: "0.1.0"
---

# PLaND Evolver

Optimize the agent's single SOP skill toward the path to least non-determinism while preserving task accuracy. Code steps bypass unnecessary model reasoning; English steps remain where semantic judgment is required.

## Inputs

Require:

- the generated agent directory;
- `evals.csv` with `input`, `output`, and `reasoning`; `id` is optional;
- a runner command that invokes the agent;
- `target_accuracy` as a quality floor;
- `optimization_metric`: `total_tokens`, `mean_latency_seconds`, or `estimated_model_cost_usd`;
- minimum objective improvement ratio;
- `max_iterations` (default: `10`), plus maximum cost and elapsed time.

Freeze the generated system prompt before baseline measurement. Keep the runtime model, system prompt, agent harness, evaluation truth, scorer, datasource snapshot, seed, and execution permissions fixed. Hide each row's `output` and `reasoning` from the runtime agent.

## Evolution loop

1. Run every development eval from an isolated initial state. Store the output, trace, latency, tokens, cost, errors, and an immutable SOP snapshot containing its text, SHA-256 hash, and English/reference/command step counts.
2. Score actual output against expected output with the task's deterministic scorer where possible. Separate infrastructure failures from agent failures.
3. Treat `target_accuracy` as a floor, not the optimization objective. Continue while a bounded change may reduce the configured expense metric without dropping below that floor.
4. Stop if the candidate-attempt count has reached `max_iterations`. If capacity remains, increment the one-based iteration, cluster failures and unnecessary expense, and propose one bounded change inside the workflow SOP package. When generating a code candidate, explicitly inspect whether stable work can be cached and whether two or more independent operations can run in parallel.
5. For each SOP step, retain one representation: a direct English instruction, a one-level relative reference, or an explicit Python/Bash command.
6. Replace an English step with a command only when the operation is mechanical, stable, locally testable, and cheaper or more reliable than model interpretation. Never hide an LLM call inside a deterministic command.
7. Rerun the same development and validation protocol. Accept the candidate only if it meets the accuracy guardrail and configured cost, latency, dependency, network, and security policies; otherwise restore the prior accepted version.
8. Record the hypothesis, diff, metrics, and accept/reject decision. For every accepted hybrid candidate, save a separate NL-versus-hybrid comparison artifact; console output alone is insufficient.

After producing comparable run JSON files, resolve the script relative to this skill and run:

```bash
python3 scripts/assess_candidate.py \
  --baseline-development <baseline-development.json> \
  --candidate-development <candidate-development.json> \
  [--candidate-validation <candidate-validation.json>] \
  [--baseline-validation <baseline-validation.json>] \
  --candidate <candidate-name> \
  --hypothesis <bounded-hypothesis> \
  --iteration <one-based-iteration> \
  [--max-iterations <positive-integer, default 10>] \
  --target-accuracy <0-to-1> \
  [--optimization-metric total_tokens|mean_latency_seconds|estimated_model_cost_usd] \
  [--min-objective-improvement-ratio <0-to-less-than-1>] \
  [--require-hybrid-sop] \
  --max-validation-latency-ratio <positive-ratio> \
  --output <decision.json>
```

Do not create or evaluate another candidate after iteration `max_iterations`. Treat `stop_iteration_limit` as a terminal result, and do not run validation when the script returns either `stop_iteration_limit` or `reject_before_validation`. Accept a candidate only when a second assessment containing validation evidence returns `accept`.

After acceptance, persist the direct comparison for each comparable split:

```bash
python3 scripts/compare_variants.py \
  --natural-language-run <initial-natural-language-run.json> \
  --hybrid-run <accepted-hybrid-run.json> \
  --output <nl-vs-hybrid-comparison.json>
```

The comparison refuses mismatched model, digest, seed, eval file, split, system-prompt hash, agent-harness hash, datasource snapshot, or scorer hash. It must retain both SOP snapshots and both absolute metric sets—not only deltas—including accuracy, correct/case counts, input/output/total tokens, estimated model cost, total/mean/p95 latency, and representation counts.

End each numbered SOP step with one machine-readable representation marker: `<!-- pland:english -->`, `<!-- pland:reference -->`, or `<!-- pland:command -->`. A hybrid SOP has at least one command step and at least one non-command step. The evaluation runner must save the marked SOP content and hash before invoking any eval case.

Read [run contract](references/run-contract.md) when implementing the harness or deciding whether a candidate is valid. Read [code policy](references/code-policy.md) before generating or accepting Python, Bash, dependencies, or network behavior.

## Allowed changes

- the workflow SOP's `SKILL.md` and its directly referenced instruction files;
- tools and Python/Bash scripts directly invoked by that SOP;
- `pyproject.toml` for approved open-source dependencies.

Do not change `instructions.md`, the system prompt, runtime model, agent harness, eval inputs, expected outputs, scorer boundary, datasource snapshot, seed, target accuracy, held-out data, or execution permissions. Candidate evaluation must reject a missing or changed frozen-invariant fingerprint. Do not introduce a new paid product or metered service without explicit authorization. Approved VPC and API endpoints may be used only when already permitted by the frozen network policy.

Generated code must minimize total expense across model tokens, wall-clock time, CPU, memory, storage, network, and service charges. Prefer the standard library, single-pass processing, bounded work, and reuse of already-computed results. Consider content-addressed caching for stable repeated computations. Consider bounded parallel execution when at least two operations are independent, concurrency cannot change semantics, and deterministic result ordering is restored before downstream use. Do not add caching or parallelism by default: record why each is safe, its invalidation or concurrency bound, and its measured end-to-end benefit. A command is not an improvement unless its end-to-end measurements justify its maintenance and execution cost.

## Stop

Success requires `validation_accuracy >= target_accuracy`, a measured improvement in `optimization_metric`, and saved NL-versus-hybrid comparison artifacts when hybrid evolution is required. Accuracy at or above the floor alone does not stop optimization. Otherwise stop after `max_iterations` candidate attempts (default `10`), or earlier at the configured cost, time, or no-improvement limit. Reaching a limit is not success: return the best accepted version and the stop reason. Report success only from comparable runs, then publish the final held-out accuracy, cost, latency, token usage, variance, and English/reference/command step counts for both the initial and evolved SOP.
