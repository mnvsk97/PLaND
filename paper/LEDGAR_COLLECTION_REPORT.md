# PLaND fresh evaluation report

## Technical summary

This collection evaluates fixed English and hybrid SOP execution on fresh, balanced LEDGAR study splits sampled solely from untouched official training rows. CFPB and SpamAssassin were not run. Each dataset has exactly 500 development, 1,000 selection, and 500 reserved final-test cases. The main results below identify the stage actually reached; a reserved test is evaluated only after selection accepts.

LEDGAR passed the stated statistical criteria on final test: accuracy was 95.6% → 95.4%, with 39.20% fewer model tokens.

These measurements test the resulting fixed packages. The construction record does not independently establish autonomous rule-discovery reliability.

## Study contract and completed scope

| Item | Frozen value |
| --- | --- |
| Study | fresh-paper-ledgar-training-20260905 |
| Model | qwen3:14b; bdbd181c33f2ed1b31c972991882db3cf4d192569092138a7d29e973cd9debe8 |
| Runtime | Native Ollama 0.33.0; DeepAgent 0.7.12; langchain-ollama 1.1.0; temperature 0; thinking disabled; complete responses at harness boundary, internally streamed Ollama HTTP transport (documented deviation); context 16,384; output cap 128; two case workers and two server slots; Flash Attention; q8_0 KV cache; one loaded model; keep alive −1 |
| Main / dataset seed | 20260902 |
| Bootstrap | 5,000 paired resamples; accuracy RNG seed 20260902; token RNG seed 20260903; two-sided 95% percentile intervals |
| Readiness | At least 80% development accuracy, complete valid outputs, no errors, at most ten English attempts |
| Candidate limit | One hybrid candidate per dataset |
| Selection | Both accuracies ≥80%; accuracy-difference CI lower bound ≥−2 pp; token reduction ≥5%; token-reduction CI lower bound >0; matching frozen invariants and no execution errors |
| Repeats | Three additional paired executions on the reached selection/final split, seeds 20260903–20260905; pair order alternates |

Token use is reported model input plus output tokens. Accuracy is exact label agreement. All comparisons use the same case identifiers and expected labels within a pair. Runtime latency is elapsed case time within a two-worker run; throughput wall time is a separate measurement.

## Main results

| Dataset | Stage | Cases | Baseline → hybrid accuracy | Difference (pp), 95% CI | Model calls | Model tokens | Token reduction, 95% CI | Criteria |
| --- | --- | ---: | --- | --- | ---: | ---: | --- | --- |
| LEDGAR | final test | 500 | 95.6% → 95.4% | -0.20; [-0.60, +0.00] | 500 → 305 | 229,001 → 139,226 | 39.20%; [34.94%, 43.68%] | Pass |

Final-test criteria are descriptive checks on the frozen package, not another selection or refinement opportunity.

## Acceptance-gate audit

| Dataset | Selection decision | Generic invariants and execution | Paired statistical gates | Reserved final test |
| --- | --- | --- | --- | --- |
| LEDGAR | accept | accept | {'noninferiority_margin': 0.02, 'minimum_token_reduction': 0.05, 'minimum_accuracy': 0.8, 'require_no_accuracy_regression': False, 'minimum_accuracy_difference_lower_bound': None, 'max_per_label_recall_drop': None, 'minimum_command_precision': None, 'quality_noninferior': True, 'token_objective_met': True, 'absolute_viability': True, 'relative_pass': True, 'test_release_pass': True} | evaluated |

## Baseline readiness and candidate provenance

| Dataset | English attempts | Development accuracy | Candidate rules | Baseline SOP SHA-256 | Candidate SOP SHA-256 |
| --- | ---: | ---: | ---: | --- | --- |
| LEDGAR | 1/10 | 95.20% | 21 | `2236217828abb3f0494a3dc10f5aba1d5b6bfe89d07fe3fbddfa41e312eb3a1d` | `839f5134b4a4e864fda13dec9a6c996c17a59789df474d842d0646d17fec8ca7` |

The host used the two PLaND skills to generate the English scaffold and construct one candidate after baseline readiness. Each candidate uses frequent 4–6-word phrases observed in at least eight development cases, with one label and correct baseline decisions on those cases. At most three complementary phrases per label are retained. Matching multiple labels, absent matches, invalid inputs, and failed output checks abstain. The command replaces S03 and retains the exact frozen English S03 as fallback. No prediction cache, paid service, or classifier network access is used.

| Dataset | Command-resolved cases | Command precision | Model fallback cases | Escape reasons |
| --- | ---: | ---: | ---: | --- |
| LEDGAR | 195 | 96.41% | 305 | {'command_abstained': 305} |

## Repeatability of the frozen comparison

| Dataset | Stage | Seed | Pair order | Baseline → hybrid accuracy | Baseline → hybrid tokens | Criteria |
| --- | --- | ---: | --- | --- | ---: | --- |
| LEDGAR | test | 20260903 | baseline → hybrid | 95.6% → 95.4% | 229,001 → 139,226 | Pass |
| LEDGAR | test | 20260904 | hybrid → baseline | 95.6% → 95.4% | 229,001 → 139,226 | Pass |
| LEDGAR | test | 20260905 | baseline → hybrid | 95.6% → 95.4% | 229,001 → 139,226 | Pass |

These executions reuse the same frozen cases; they are not independent test samples. No repeat changed the selected package.

| Dataset / variant | Mean accuracy ± sample SD | Mean tokens ± sample SD | Token range | Cases with any label disagreement | Pairwise disagreements |
| --- | --- | --- | --- | ---: | --- |
| LEDGAR / baseline | 95.60% ± 0.000 pp | 229,001.00 ± 0.00 | 229,001–229,001 | 0 | [0, 0, 0] |
| LEDGAR / hybrid | 95.40% ± 0.000 pp | 139,226.00 ± 0.00 | 139,226–139,226 | 0 | [0, 0, 0] |

## Data integrity and comparability

| Dataset | Split counts | Duplicate / overlapping cases | Plan SHA-256 | Data audit |
| --- | --- | --- | --- | --- |
| LEDGAR | 500 / 1,000 / 500 | IDs: 0; content: 0; prior overlap: 0 | `723718d1991f91a524ded17c7e3d0c8957040a385f55feb50c0d140dd9456ec5` | [Passed](../experiments/fresh-paper-ledgar-training-20260905/ledgar/results/dataset-audit.json) |

Source hashes, full data-selection fingerprints, baseline/candidate package fingerprints, seeds, original commands, traces, failure logs, and release timestamps are retained in each dataset evidence directory. Raw benchmark inputs remain local under upstream terms.

## Runtime measurements

| Dataset | Mean case time baseline → hybrid (s) | p95 case time (s) | Throughput wall time (s) | Max runner RSS baseline → hybrid (bytes) |
| --- | --- | --- | --- | --- |
| LEDGAR | 0.9441 → 0.5876 | 1.4808 → 1.3087 | 236.93 → 147.36 | 156,024,832 → 158,138,368 |

Local API charges were zero; this is not a measurement of hardware cost, electricity, total operational cost, or dollar savings. Runner RSS excludes the separately resident Ollama model.

## Paper-ready findings

### Methods paragraph

We evaluated fixed English and hybrid SOPs on balanced LEDGAR clause-classification study splits sampled solely from untouched official training rows. Each dataset contained 500 development, 1,000 selection, and 500 reserved test examples. Previously opened identifiers and normalized-content duplicates were excluded, and new disjoint study splits were constructed within the official LEDGAR training partition; these are not official benchmark validation/test scores. An English baseline had to reach 80% development accuracy with complete, error-free execution before one hybrid candidate could be constructed. The hybrid used development-derived phrase rules and the exact frozen English fallback. Model-mediated execution used DeepAgent with local qwen3:14b, temperature zero, thinking disabled, and two concurrent workers. Selection required both workflows to reach 80% accuracy, a paired 95% accuracy-difference interval lower bound of at least −2 percentage points, at least 5% fewer model tokens, and a strictly positive lower bound for token reduction. We used 5,000 paired bootstrap resamples. Only selection acceptance released the reserved test.

### Results paragraph

On LEDGAR's 500-case reserved test, accuracy changed from 95.6% to 95.4%; model calls changed from 500 to 305, and tokens from 229,001 to 139,226 (39.20% reduction). The fixed package met the stated statistical criteria at this stage.

### Repeatability paragraph

Three additional paired executions used the same frozen packages and the same reached evaluation split, with inference seeds 20260903, 20260904, and 20260905. The repeat table reports each result separately, and the variability table gives sample standard deviations and prediction disagreements. These are repeated executions, not new evaluation samples or further candidate attempts.

### Limitations paragraph

The evidence is limited to one local model, balanced subsets, and the specific fixed SOP packages. The data do not represent natural production label frequencies. Freshness means no prior local experimental exposure; it does not establish absence from Qwen pretraining. All three study splits were sampled from official training rows, so these results are not official LEDGAR benchmark validation/test scores. Development phrase purity does not guarantee correctness on unseen documents; the paired evaluation is the relevant safeguard. Bootstrap intervals describe sampled-case uncertainty within these prepared tasks and do not cover model changes or distribution shift. The construction trail does not independently test autonomous rule discovery. Full business workflows, production readiness, energy use, and monetary savings were not evaluated. Any dataset rejected before final test has no reserved-test estimate.

## Verification and disposition

Dataset integrity, run arithmetic, model-token accounting, frozen pair fingerprints, statistical recomputation, and release order passed the saved collection audits. The separate repository/report audit receipt records final manifest verification. This report supplies replacement manuscript text and exact results; the existing PLaND.pdf is not changed by this report builder.

## Remaining questions

The statistical outcomes are fixed. Any future candidate revision requires a new development process and unused evaluation evidence.

## Disclosed transport deviation

Transport metadata correction: the harness received complete responses, while Ollama used HTTP `stream: true` internally. Both arms used the same frozen path and aggregated responses before scoring. Raw `stream: false` fields are preserved as recorded, but are superseded for wire-level interpretation by the audited runtime metadata. No measurements or packages changed; the disposition is recorded in `protocol/ledgar-transport-disposition.json`.

## Host and execution environment

Apple M5 Pro; 18 logical CPUs; 48 GiB unified memory; macOS 26.6.2; arm64; Python 3.14.7. Native Ollama and package versions were verified in `results/runtime-audit.json`.

## Detailed paper statistics and provenance

Frozen run commit: `6a9672ba02b07e282146f1c4c7f7b3d2f48701c3`. Immutable case-evidence manifest: `experiments/fresh-paper-ledgar-training-20260905/ledgar/case-evidence-manifest.json`, SHA-256 `44dce8eb6ffa79e7bf6fdc011bc6334dd5996cca526ae4c21d760d42e5b3eca5`.

The earlier collection was invalidated because its exclusion list missed 18 previously used pilot cases. Its complete sample was quarantined; no predictions or generated rules from it enter this report. The restart used a newly generated English package and a candidate constructed only from the new development traces. The frozen plan contains a descriptive label-manifest path typo; the actual recorded preparer command used the existing confirmatory label manifest. The exact path, hash and unchanged ten-label vocabulary are recorded in `protocol/path-resolution.json`.

| Data fingerprint | SHA-256 |
| --- | --- |
| evals_sha256 | `0cb73326d9de4277f5f709b5ebb5e13c5bf3ce4e9953633178cecd99436af3bf` |
| selection_sha256 | `4506bd6e59e106b79babdf54b8f4f6f0c2f5ad9e4d27268575a1d7105cb03440` |
| case_manifest_sha256 | `9c2a5992135575e995827ead15c5ad17e3f628a911e714e6bbf81a262b0f224c` |
| Source train.jsonl | `d715cde50f04e36401b76704d693cedc2697169dbcbc97c8c8519767edfe94ec` |
| Source validation.jsonl | `5890aaee646adf03ca9665c1207b2a1ec95f60007c3e8a86f36b753992786ce1` |
| Source test.jsonl | `d78bb9c8e149b169bfb4c2e910d21c6fea32968c11a5aff880f2ef6fb86bd86c` |

Candidate skill-content SHA-256: `c09ab1d6ccdc3939e3b51eb23a06c28b3087800f14b726998ad2863da4c5aec3`.

| Main statistic | Baseline | Hybrid |
| --- | ---: | ---: |
| Correct / cases | 478 / 500 | 477 / 500 |
| Macro F1 | 0.956118 | 0.954120 |
| Accuracy Wilson 95% CI | [93.43%, 97.08%] | [93.19%, 96.92%] |
| Input tokens | 225,235 | 136,967 |
| Output tokens | 3,766 | 2,259 |
| Command attempts | 0 | 500 |

Exact paired McNemar p-value: 1. Correctness table: `{'both_correct': 477, 'natural_language_only': 1, 'hybrid_only': 0, 'both_wrong': 22}`.

| Label | Baseline recall | Hybrid recall | Difference (pp) |
| --- | ---: | ---: | ---: |
| Amendments | 92.00% | 92.00% | +0.00 |
| Assignments | 98.00% | 98.00% | +0.00 |
| Counterparts | 100.00% | 100.00% | +0.00 |
| Entire Agreements | 98.00% | 96.00% | -2.00 |
| Expenses | 98.00% | 98.00% | +0.00 |
| Governing Laws | 98.00% | 98.00% | +0.00 |
| Notices | 94.00% | 94.00% | +0.00 |
| Severability | 94.00% | 94.00% | +0.00 |
| Survival | 96.00% | 96.00% | +0.00 |
| Terms | 88.00% | 88.00% | +0.00 |

CFPB and SpamAssassin: not run in this approved phase. Main manuscript and PDF integration: deferred; this report does not claim the existing paper contains these numbers.
