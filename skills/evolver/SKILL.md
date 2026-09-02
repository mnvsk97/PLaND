---
name: evolver
description: Evolve an agent SOP from evaluation evidence by replacing suitable prose reasoning with deterministic rules or code while tracking accuracy, cost, and latency. Use for controlled skill optimization, not unapproved production experimentation.
---

# Evolve a deterministic skill

Improve an agent and its `SOP.md` through repeatable evaluation. The unit of evidence is a runner result on a fixed evaluation case, not an intuition about wording.

## Required state

Before changing the SOP, locate:

- evaluation inputs and expected outputs or a scoring rubric;
- the runner for the selected agent (`codex`, `claude code`, `deepagents`, or another configured adapter);
- the current `SOP.md` and `EVOLVER.md`;
- the accuracy, cost, and latency measurements;
- the production-data policy.

If the experiment is not initialized, use the `init` skill. Do not infer missing ground truth, runner behavior, or production authorization.

## Evolution loop

1. Freeze the evaluation set and record the baseline version of the agent and SOP.
2. Run the baseline through the configured runner. Save per-case output, score, token or monetary cost, latency, and errors.
3. Group failures by repeatable cause. Record a pattern only when the evidence identifies a reusable behavior, not a single desired answer.
4. Propose one bounded change at a time:
   - tighten or reorder an SOP instruction;
   - add a deterministic rule;
   - replace a stable prose operation with a script;
   - add structured parsing, counting, validation, or formatting.
5. Run the same evaluation set with the candidate change.
6. Compare baseline and candidate using the acceptance policy in `EVOLVER.md`.
7. Accept the change only if it satisfies the stated accuracy guardrail and cost/latency tradeoff. Otherwise revert the candidate and retain the result as evidence.
8. Update `SOP.md`, `.rule/`, and `INVENTORY.json` only for accepted changes. Preserve the run record for both accepted and rejected candidates.

Never tune on hidden test cases. Keep development cases separate from the final evaluation set when both are available.

## Converting prose to code

Prefer code when the operation is mechanical, stable, testable, and cheaper than model reasoning. Examples include extracting page one, counting pages or tokens, parsing headers, normalizing fields, applying exact mappings, and validating output schemas.

Keep prose reasoning when the operation requires semantic judgment, contextual interpretation, or adaptation to genuinely novel inputs. A document classifier may use deterministic extraction and counting before asking the model to interpret the remaining evidence and select a known bucket.

Every script introduced into the SOP must have:

- a documented input and output contract;
- deterministic behavior for the same inputs;
- explicit failure behavior;
- a direct test covering at least one success and one failure case;
- a measured effect on the configured metrics.

## Production boundary

- `none`: use no production runs or production-derived examples.
- `few`: use only the explicitly approved production examples, record their identifiers, and do not fold them into the final held-out evaluation set.

## Reporting

For each iteration, report the hypothesis, changed artifacts, evaluation-set identity, accuracy delta, cost delta, latency delta, failures, and accept/reject decision. Do not claim improvement without comparable measurements.

Use [references/experiment-format.md](references/experiment-format.md) when creating run records or updating the inventory.
