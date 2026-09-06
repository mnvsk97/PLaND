# PLaND fresh paper collection

**Status:** Approved by the author on 2026-09-05 in the `data collection` task:
“Approve the existing plan.” The approval question explicitly enumerated the
80% floor, -2 percentage-point bound, 5% token reduction, 5,000 bootstrap
samples, at most ten baseline attempts, one hybrid candidate, three repeats,
500/1,000/500 splits, and LEDGAR → CFPB → SpamAssassin order.
Matching dataset-specific JSON plans freeze these settings before collection.

## Why collect new data

The recent implementation changes strengthen baseline readiness, paired
comparison, executable-step provenance, and exact model fallback. The old run
records predate those changes. This study collects a fresh evidence set from
scratch under the revised implementation while preserving the paper's existing
claim boundaries.

The reported evidence evaluates the execution of the resulting fixed English
and hybrid SOP packages. A complete construction trail will be retained, but
this single study will not be presented as an independent evaluation of how
reliably an autonomous agent discovers useful rules. It also will not support
claims about complete business workflows, production deployment, lower output
variability, dollar savings, or energy savings.

## Recommended research question

For each of the paper's three classification tasks, can a fixed hybrid SOP use
selective Python execution with model fallback to reduce model-token use while
preserving classification accuracy under the paper's predeclared acceptance
criteria?

## Recommended scope

- Tasks: LEDGAR clause classification, CFPB complaint classification, and
  SpamAssassin email classification.
- Labels: retain the paper's existing ten LEDGAR labels, ten CFPB labels, and
  two SpamAssassin labels for comparability.
- Host/orchestration environment: Codex invokes the two PLaND skills. Record
  its model identifier, reasoning setting, prompts, messages, generated files,
  diffs, decisions, and timestamps for provenance. This record documents how
  the packages were constructed; it is not an autonomous-discovery success
  rate or a compared per-case execution model.
- Evaluated execution model: local Ollama `qwen3:14b`, pinned by its full model
  digest, with thinking and streaming disabled and temperature zero.
- PLaND remains a two-skill methodology. The data-collection skill only records
  and gates experiment operations.

## Recommended data boundaries

Prepare and freeze all three splits together for each dataset:

| Split role | Cases per dataset | Permitted use |
| --- | ---: | --- |
| Development | 500 | Baseline clarification and candidate generation |
| Selection | 1,000 | One paired baseline/candidate selection decision |
| Final test | 500 | One paired final report after selection passes |

Exclude every previously opened case by identifier and normalized content.
For LEDGAR, preserve the official upstream train/validation/test boundaries.
For CFPB and SpamAssassin, deterministically create non-overlapping balanced
splits from the frozen source snapshot. Preserve raw licensed data locally and
publish hashes, counts, selection rules, exclusions, and safe evidence only.

Use dataset-selection seed `20260902`, matching the paper's frozen protocol.
The eligible source pool will differ because all previously opened identifiers
and normalized content are excluded.

## Recommended baseline-readiness stage

1. `generate-initial-version` creates one entirely English SOP from the task
   contract without access to selection or final-test answers.
2. Run the English baseline on the 500 development cases.
3. If accuracy is below 80%, the host may make one bounded English-only
   clarification using development traces and rerun development.
4. Stop when the baseline reaches at least 80% accuracy with normal completion
   and no run errors, or after ten recorded baseline attempts.
5. If attempt ten is still nonviable, end that dataset as
   `baseline_nonviable`. Do not generate a hybrid candidate.
6. Once viable, freeze the complete English baseline, exact fallback contract,
   prompt, runner, scorer, dataset, runtime, permissions, dependencies, and
   hashes.

## Recommended candidate stage

1. Give `pland-evolver` only the frozen task contract, English baseline,
   development inputs, and development run traces.
2. Permit exactly one hybrid candidate per dataset for this study.
3. Every executable command step must retain and link to the exact frozen
   English instruction it replaces. Command failure, abstention, or invalid
   output returns to that English fallback.
4. A command-produced classification must include a valid label and a
   traceable `matched_rule`. Do not use a decorative numeric confidence.
5. Run baseline and candidate on identical development cases. Reject before
   selection if the candidate is below the quality floor, has execution errors,
   or does not improve the chosen expense objective.

The candidate-generation record establishes provenance only. The paper result
is the paired evaluation of the fixed baseline and fixed candidate, consistent
with the existing PDF.

## Recommended selection gate

Run the frozen baseline and candidate once on the same 1,000 selection cases
under identical model, digest, prompt, runner, scorer, seed, runtime,
permissions, and evaluation inputs. Only the SOP package may differ.

Selection passes only when all of the following hold:

1. Every frozen fingerprint matches.
2. Baseline and candidate accuracy are each at least 80%.
3. The lower endpoint of the paired 95% bootstrap interval for
   `accuracy_candidate - accuracy_baseline` is at least -0.02.
4. Token reduction is at least 5%, and the lower endpoint of its paired 95%
   bootstrap interval is positive.
5. There are no unaccounted execution or output-schema errors.

Use 5,000 paired bootstrap resamples with bootstrap seed `20260902`. Use paired
inference seed `20260902` for the main comparison.

If selection rejects the candidate, end that dataset and keep its final test
unopened. Do not create a second candidate from selection observations.

## Recommended final-test stage

If and only if selection passes, run the frozen baseline and candidate once on
the same 500 final-test cases. Report the result whether it passes or fails.
Do not revise either package or rerun final test in response to the outcome.

The final result is descriptive evidence from the reserved sample, not another
selection gate. Report accuracy, macro F1, model calls, command calls, fallback
calls, input/output/total tokens, latency, direct service cost, resource use,
paired bootstrap intervals, Wilson intervals, exact McNemar result, per-label
recall, command precision, every escape reason, and case-level correctness.

To preserve the PDF's repeatability claim, run three additional paired
executions of the same frozen baseline and hybrid packages on the stage reached
by each dataset: final test for a dataset that passed selection, otherwise the
selection split. Use inference seeds `20260903`, `20260904`, and `20260905`,
alternate pair order as baseline/hybrid, hybrid/baseline, baseline/hybrid, and
report the repeated measurements separately from the main comparison. These
are repeated executions, not additional independent samples or candidate
attempts.

## Authorized runtime

Use one identical runtime for every baseline/candidate pair. Two workers are
authorized to keep collection practical. Wall time must be
described as throughput under two-request parallelism rather than single-case
latency. Freeze context length, output limit, keep-alive, Flash Attention, KV
cache type, loaded-model limit, and Ollama version in the final plan.

## Evidence and paper integration

For every attempt and split, retain the exact argv, stdout/stderr log,
checkpoint, raw safe result, case IDs, predictions, traces, hashes, model
digest, runtime, token counts, comparison, and decision. Preserve failed runs
and retries instead of overwriting them. Generate a study manifest covering all
evidence files.

The fresh study is intended to replace the paper's current numerical evidence
regardless of which datasets pass or fail. Preserve the old evidence as
historical material, but do not mix or pool it with the fresh runs. Update the
paper audit so every replacement number is recomputed from the new case-level
records. The paper must keep the same claim scope and report the actual stage
reached by each dataset; a selection result must not be renamed as a final-test
result.

## Recorded author decisions

1. Approved the 80% quality floor, two-percentage-point
   non-inferiority margin, 5% token-reduction target, and 5,000 bootstrap
   resamples.
2. Approved the ten-attempt English-baseline limit and one-candidate
   limit.
3. Approved two-worker execution and machine-specific Ollama configuration.
4. Approved that the fresh results replace the paper's current numerical results
   regardless of outcome, with old evidence retained separately.

The 500 development / 1,000 selection / 500 final-test split is fixed and is not
an open decision. The dataset-selection, main inference, and bootstrap seed are
`20260902`; repeat inference seeds are `20260903` through `20260905`.

Freeze matching JSON plans and repository state before dataset collection.
Execute LEDGAR to its valid terminal stage before CFPB, then SpamAssassin.
The model-mediated English path executes through LangChain DeepAgent with
local Qwen. The harness supplies the fixed SOP, labels, and one document as
the request; no evaluation answers or other records are exposed. Deterministic
hybrid routes may bypass model work; every escape executes the identical
English DeepAgent path. Report this task-local execution design explicitly.
