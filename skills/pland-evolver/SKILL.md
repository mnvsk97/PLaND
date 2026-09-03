---
name: pland-evolver
description: Improve a generated DeepAgent by evaluating its single SOP skill and replacing eligible English steps with verified Python or Bash commands. Use after generate-initial-version when labeled evals and an accuracy target are available.
metadata:
  project: pland
  version: "0.2.0"
---

# PLaND Evolver

Optimize the agent's single SOP skill toward the path to least non-determinism while preserving task accuracy. Code steps bypass unnecessary model reasoning; English steps remain where semantic judgment is required.

## Inputs

Require:

- the generated agent directory;
- `evals.csv` with `input`, `output`, and `reasoning`; `id` is optional;
- a runner command that invokes the agent;
- a primary quality measure and `target_quality` floor supplied by the task's scorer;
- a task-supplied quality policy defining any baseline-relative, uncertainty,
  slice, route, or structural guardrails required in addition to the floor;
- `optimization_metric`: `total_tokens`, `mean_latency_seconds`, or `estimated_model_cost_usd`;
- minimum objective improvement ratio;
- `max_iterations` (default: `10`), plus maximum cost and elapsed time.

Freeze the generated system prompt before baseline measurement. Keep the runtime model, system prompt, agent harness, evaluation truth, scorer, datasource snapshot, seed, and execution permissions fixed. Hide each row's `output` and `reasoning` from the runtime agent.

## Evolution loop

1. Run every development eval from an isolated initial state. Store the output, trace, latency, tokens, cost, errors, and an immutable SOP snapshot containing its text, SHA-256 hash, and English/reference/command step counts.
2. Score actual output against expected output with the task's deterministic scorer where possible. Separate infrastructure failures from agent failures.
3. Check baseline viability before expense optimization using the configured task-quality measure and normal-completion requirement. If it fails, stop with `baseline_nonviable`; repairing the model, harness, tool interface, perception layer, evaluator, or execution budget requires a newly frozen baseline.
4. Stop if the candidate-attempt count has reached `max_iterations`. If capacity remains, increment the one-based iteration, cluster development failures and unnecessary expense, and propose one bounded change inside the workflow SOP package. Never mine validation or held-out cases for candidate rules. When generating a code candidate, explicitly inspect whether stable work can be cached and whether two or more independent operations can run in parallel.
5. For each SOP step, retain one representation: a direct English instruction, a one-level relative reference, or an explicit Python/Bash command.
6. Replace an English step with a command only when the operation is mechanical, stable, locally testable, and cheaper or more reliable than model interpretation. Never hide an LLM call inside a deterministic command.
7. Preserve the complete accepted English path as the command's fallback. Do
   not shorten or rewrite that path in the same candidate that introduces a
   command; evaluate any later instruction compression as its own bounded
   change.
8. Rerun the same development and validation protocol. A final acceptance requires both candidate and baseline validation runs on the same frozen eval set. Accept the candidate only if it meets the primary quality floor, every task-supplied guardrail, and configured cost, latency, dependency, network, and security policies; otherwise restore the prior accepted version.
9. Record the hypothesis, diff, metrics, and accept/reject decision. For every accepted hybrid candidate, save a separate NL-versus-hybrid comparison artifact; console output alone is insufficient.

## Generic and task-local boundaries

Keep this skill independent of datasets, labels, domains, and benchmark-specific
thresholds. The task-local scorer owns the quality measure and optional
guardrails such as confidence-interval bounds, slice degradation, command-route
precision, schema validity, or final-state invariants. The evolver consumes only
their recorded values and pass/fail decisions.

An unchanged rerun is a replication, not another evolution iteration. Lock the
candidate before replications begin. Replications measure variability and may
confirm acceptance or rejection, but their cases and outcomes cannot be used to
edit that candidate. Once any held-out result is opened, stop evolving and
report the result.

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
  --target-quality <0-to-1> \
  [--minimum-baseline-quality <0-to-1>] \
  [--non-inferiority-margin <0-to-1>] \
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

Keep each stable baseline step identifier and end every numbered SOP step with one machine-readable representation marker: `<!-- pland:english -->`, `<!-- pland:reference -->`, or `<!-- pland:command -->`. A script counts as a command step only when the evaluated runtime invokes it and its result performs, controls, validates, or replaces that step. A script that only produces text for later model interpretation is a reference transformation. A hybrid SOP has at least one command step and at least one non-command step. Save the marked SOP content and full SHA-256 before any eval case.

Every command candidate retains its original English instruction as fallback. Derive preconditions and output guards from the supplied requirements, policy, tool schemas, and development traces; never embed benchmark- or domain-specific rules in PLaND itself. Escape to English when a precondition, execution, required verification, or guard fails. Record the step ID, escape reason, model work, and command work. Generated tool arguments require provenance from runtime input, an earlier tool result, or deterministic derivation. A guard is enforced only when runtime execution passes through it; otherwise keep the step English.

Read [run contract](references/run-contract.md) when implementing the harness or deciding whether a candidate is valid. Read [code policy](references/code-policy.md) before generating or accepting Python, Bash, dependencies, or network behavior.

## Allowed changes

- the workflow SOP's `SKILL.md` and its directly referenced instruction files;
- tools and Python/Bash scripts directly invoked by that SOP;
- `pyproject.toml` for approved open-source dependencies.

Do not change `instructions.md`, the system prompt, runtime model, agent harness, eval inputs, expected outputs, scorer boundary, datasource snapshot, seed, target quality, held-out data, or execution permissions. Candidate evaluation must reject a missing or changed frozen-invariant fingerprint. Do not introduce a new paid product or metered service without explicit authorization. Approved VPC and API endpoints may be used only when already permitted by the frozen network policy.

Generated code must minimize total expense across model tokens, wall-clock time, CPU, memory, storage, network, and service charges. Prefer the standard library, single-pass processing, bounded work, and reuse of already-computed results. Consider content-addressed caching for stable repeated computations. Consider bounded parallel execution when at least two operations are independent, concurrency cannot change semantics, and deterministic result ordering is restored before downstream use. Do not add caching or parallelism by default: record why each is safe, its invalidation or concurrency bound, and its measured end-to-end benefit. A command is not an improvement unless its end-to-end measurements justify its maintenance and execution cost.

## Stop

Success requires validation quality at or above `target_quality`, every enabled task-local guardrail to pass, a strictly lower value for the configured expense objective when its minimum improvement is zero (or the configured proportional reduction otherwise), and saved NL-versus-hybrid comparison artifacts when hybrid evolution is required. The task supplies the scorer and names the primary quality measure; PLaND does not assume accuracy, labels, extracted fields, final-state shape, output type, or which secondary guardrails apply. Final acceptance requires the matching baseline-validation artifact; candidate validation alone is insufficient. Quality at or above the floor alone does not stop optimization. Otherwise stop after `max_iterations` candidate attempts (default `10`), or earlier at the configured cost, time, or no-improvement limit. Reaching a limit is not success: return the best accepted version and the stop reason. Report success only from comparable runs, then publish the final held-out quality, cost, latency, token usage, variance, and English/reference/command step counts for both the initial and evolved SOP.

Canary monitoring is optional and prospective; never repartition completed frozen data to manufacture it. Canary evidence is unavailable to candidate mining and may restore only a previously validated complete SOP, not create an unvalidated mixture through step-by-step demotion. Keep deployed and last-validation-tested identities distinct. Continual monitoring remains proposed unless an actual monitor and evidence exist.
