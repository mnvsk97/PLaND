# PLaND fresh evaluation report

> This is the required post-collection report shape. Replace bracketed fields
> only from the final audited evidence manifest and saved case-level results.
> Remove these template instructions from the generated report. Never replace
> an unopened or unreached stage with an estimate.

## Technical summary

[State in 3-5 sentences what happened across LEDGAR, CFPB, and SpamAssassin.
Name the stage reached by each dataset. State which fixed hybrid packages met
all four predeclared acceptance requirements, the observed accuracy changes,
model-call changes, and token reductions. Distinguish selection evidence from
final-test evidence. End with the narrow paper interpretation: the results test
fixed English versus hybrid SOP execution and do not independently establish
autonomous rule-discovery reliability.]

## Study contract and completed scope

| Item | Frozen value |
| --- | --- |
| Study ID | `[study_id]` |
| Git commit | `[git_head]` |
| Plan SHA-256 | `[plan_sha256]` |
| Evidence manifest | `[manifest_path and sha256]` |
| Datasets | LEDGAR; CFPB; SpamAssassin |
| Split sizes per dataset | 500 development; 1,000 selection; 500 final test |
| Evaluated model | `[model name; local digest or hosted provider/endpoint/configuration hash]` |
| Main inference seed | `[seed]` |
| Runtime | `[provider, temperature/reasoning, streaming, context, output cap, workers, client and service versions]` |
| Baseline readiness | Accuracy >=80%; normal completion; no run errors; maximum 10 English attempts |
| Candidate budget | [Approved development-attempt maximum]; first development-ready candidate only goes to selection |
| Selection gates | Both accuracies >=80%; paired accuracy lower bound >=-2 pp; tokens reduced >=5%; paired token-reduction lower bound >0 |
| Uncertainty | 5,000 paired bootstrap resamples; Wilson intervals; exact McNemar test |

Collection outcome: `[complete / partially complete / stopped]`. `[N]` model
run commands completed, `[N]` failed attempts were retained, and `[N]` reserved
final-test splits remained unopened.

## Main results

| Dataset | Reported stage | Cases | Baseline accuracy | Hybrid accuracy | Difference (pp), 95% paired CI | Baseline -> hybrid model calls | Baseline -> hybrid tokens | Token reduction, 95% paired CI | Decision |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | --- | --- |
| LEDGAR | `[selection/final test/not reached]` | `[N]` | `[x.x%]` | `[x.x%]` | `[delta; low, high]` | `[N -> N]` | `[N -> N]` | `[x.x%; low, high]` | `[Pass/Reject/Not reached]` |
| CFPB | `[selection/final test/not reached]` | `[N]` | `[x.x%]` | `[x.x%]` | `[delta; low, high]` | `[N -> N]` | `[N -> N]` | `[x.x%; low, high]` | `[Pass/Reject/Not reached]` |
| SpamAssassin | `[selection/final test/not reached]` | `[N]` | `[x.x%]` | `[x.x%]` | `[delta; low, high]` | `[N -> N]` | `[N -> N]` | `[x.x%; low, high]` | `[Pass/Reject/Not reached]` |

[For each dataset, write one short result paragraph. Lead with the decision and
stage, then give accuracy, uncertainty, model calls, tokens, and the specific
gate that passed or failed. Do not describe a selection result as a final-test
estimate.]

## Acceptance-gate audit

| Dataset and stage | Frozen invariants | Baseline >=80% | Hybrid >=80% | Accuracy lower bound >=-2 pp | Tokens reduced >=5% | Token lower bound >0 | Overall |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LEDGAR - selection | `[Pass/Fail]` | `[Pass/Fail]` | `[Pass/Fail]` | `[Pass/Fail]` | `[Pass/Fail]` | `[Pass/Fail]` | `[Pass/Reject]` |
| CFPB - selection | `[Pass/Fail]` | `[Pass/Fail]` | `[Pass/Fail]` | `[Pass/Fail]` | `[Pass/Fail]` | `[Pass/Fail]` | `[Pass/Reject]` |
| SpamAssassin - selection | `[Pass/Fail]` | `[Pass/Fail]` | `[Pass/Fail]` | `[Pass/Fail]` | `[Pass/Fail]` | `[Pass/Fail]` | `[Pass/Reject]` |

[Add final-test rows only for datasets whose selection row passed. Final-test
rows report the frozen package outcome; they do not trigger another revision.]

## Baseline readiness and candidate provenance

| Dataset | English attempts used | Frozen baseline development accuracy | Baseline SOP SHA-256 | Candidate ID | Candidate hypothesis | Command step and exact fallback | Classifier/package SHA-256 | Development decision |
| --- | ---: | ---: | --- | --- | --- | --- | --- | --- |
| LEDGAR | `[N/10]` | `[x.x%]` | `[hash]` | `[id/not created]` | `[one sentence]` | `[step ID -> fallback ID]` | `[hash/not created]` | `[Ready/Rejected/Nonviable]` |
| CFPB | `[N/10]` | `[x.x%]` | `[hash]` | `[id/not created]` | `[one sentence]` | `[step ID -> fallback ID]` | `[hash/not created]` | `[Ready/Rejected/Nonviable]` |
| SpamAssassin | `[N/10]` | `[x.x%]` | `[hash]` | `[id/not created]` | `[one sentence]` | `[step ID -> fallback ID]` | `[hash/not created]` | `[Ready/Rejected/Nonviable]` |

[Summarize what deterministic work each fixed candidate performed and when it
fell back to the model. Report `matched_rule` coverage, command precision,
abstentions, guard failures, execution failures, and fallback rate. This is a
provenance description, not an autonomous-discovery success-rate claim.]

## Repeatability of the frozen comparison

| Dataset and reported stage | Seed | Pair order | Baseline accuracy | Hybrid accuracy | Baseline tokens | Hybrid tokens | Decision |
| --- | ---: | --- | ---: | ---: | ---: | ---: | --- |
| `[dataset-stage]` | `[seed 1]` | Baseline -> hybrid | `[x.x%]` | `[x.x%]` | `[N]` | `[N]` | `[Pass/Reject]` |
| `[dataset-stage]` | `[seed 2]` | Hybrid -> baseline | `[x.x%]` | `[x.x%]` | `[N]` | `[N]` | `[Pass/Reject]` |
| `[dataset-stage]` | `[seed 3]` | Baseline -> hybrid | `[x.x%]` | `[x.x%]` | `[N]` | `[N]` | `[Pass/Reject]` |

[Repeat the three rows for each dataset. Then report mean, sample standard
deviation, range, label agreement, and pairwise disagreement. State explicitly
that these reuse the same prepared cases and are not independent samples.]

## Data integrity and comparability

| Dataset | Source snapshot SHA-256 | `evals.csv` SHA-256 | Selection-manifest SHA-256 | Development / selection / final counts | Duplicate IDs | Duplicate normalized content | Prior-case overlap | Status |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | --- |
| LEDGAR | `[hash]` | `[hash]` | `[hash]` | `500 / 1,000 / 500` | `[0]` | `[0]` | `[0]` | `[Pass/Fail]` |
| CFPB | `[hash]` | `[hash]` | `[hash]` | `500 / 1,000 / 500` | `[0]` | `[0]` | `[0]` | `[Pass/Fail]` |
| SpamAssassin | `[hash]` | `[hash]` | `[hash]` | `500 / 1,000 / 500` | `[0]` | `[0]` | `[0]` | `[Pass/Fail]` |

Baseline and hybrid runs were considered comparable only when case identifiers,
dataset bytes, model identity, system prompt, runner, scorer, inference seed,
runtime, permissions, and frozen baseline fallback contract matched.

## Paper-ready findings

### Methods paragraph

[Generate a concise paragraph describing the three datasets, fixed 500/1,000/500
split, exclusion of all previously opened identifiers and normalized content,
balanced label selection, frozen evaluated model/runtime, paired baseline/hybrid
execution, exact-match accuracy, token measurement, and four selection gates.]

### Results paragraph

[Generate a concise paragraph using only the main-results table. State the
reported stage and sample size for every dataset, all pass/reject outcomes, and
the principal accuracy, model-call, and token changes.]

### Repeatability paragraph

[Generate a concise paragraph using only the repeatability table. Separate
these repeated executions from the main comparison and do not call them new
test samples.]

### Limitations paragraph

[State that the study uses one evaluated model, balanced classification subsets,
and fixed SOP packages. It does not independently measure autonomous discovery
reliability, full workflows, production distribution shift, dollar or energy
savings, or reduced output variability unless the collected evidence directly
supports the latter. Identify any dataset that did not reach final test.]

## Verification and disposition

| Check | Result | Evidence |
| --- | --- | --- |
| Collection manifest verifies | `[Pass/Fail]` | `[path and sha256]` |
| Dataset audits pass | `[Pass/Fail]` | `[paths]` |
| Run-contract audits pass | `[Pass/Fail]` | `[paths]` |
| Statistical recomputation matches | `[Pass/Fail]` | `[paths]` |
| Repository verifier passes | `[Pass/Fail]` | `[command and receipt]` |
| Paper audit passes after integration | `[Pass/Fail/Not yet run]` | `[command and receipt]` |
| PDF rendered-page inspection passes | `[Pass/Fail/Not yet run]` | `[artifact path]` |

**Disposition:** `[Paper-ready / Evidence complete but paper integration pending /
Stopped at baseline / Rejected on development / Rejected on selection / Failed]`.

**Supported conclusion:** [One restrained conclusion based on the observed
stage and audited evidence.]

**Unsupported conclusions:** autonomous rule-discovery reliability, complete
business-workflow effectiveness, production readiness, and unmeasured cost,
energy, or variability claims.

## Remaining questions

[List only unresolved issues that could change interpretation or paper wording.
If none remain, state “None after the recorded audits.”]
