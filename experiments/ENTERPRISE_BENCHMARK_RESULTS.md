# Enterprise benchmark results

This file separates completed confirmatory measurements from pilot evidence and
prepared-only datasets. All completed model runs used local Ollama
`qwen3:14b`, seed `20260902`, no paid API, and frozen prompts, harnesses,
scorers, expected outputs, data snapshots, and execution permissions. Evolution
was restricted to the permitted SOP skill package.

## Optimized post-change replication

On 2026-09-02, the text-classification validations and the LEDGAR test were
repeated with the same `qwen3:14b` digest using a 4,096-token context, exact
JSON schema, thinking disabled, model preloading, Flash Attention, q8_0 KV
cache, and two parallel requests. Runtime settings were added to the frozen
comparison contract. These runs evaluate the existing experiment skills under
the strengthened contract; they do not regenerate or re-evolve every skill.

| Workflow and split | NL accuracy | Hybrid accuracy | Token reduction | Decision |
| --- | ---: | ---: | ---: | --- |
| LEDGAR validation (100) | 93% | 94% | 43.19% | Pass |
| LEDGAR test replication (1,000) | 93.7% | 92.9% | 40.02% | Pass |
| CFPB validation (100) | 78% | 71% | 43.26% | Reject |
| SpamAssassin validation (100) | 88% | 84% | 5.04% | Reject |

The LEDGAR replication again reduced model calls from 1,000 to 589 while the
paired accuracy-difference interval remained within the two-point margin. The
test cases were no longer untouched, so this is reproducibility evidence and
does not replace the original confirmatory release. Parallel wall time measures
collection throughput and is not directly comparable with sequential latency.

## Confirmatory results

The confirmatory gate requires both NL and hybrid accuracy of at least 80%, a
paired hybrid-minus-NL accuracy 95% interval whose lower bound is at least -2
percentage points, and at least 5% token reduction with a positive 95% lower
bound. The test set is released only after validation passes.

| Workflow and split | NL quality | Hybrid quality | NL tokens | Hybrid tokens | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| LEDGAR validation (100) | 92.0% accuracy; 0.9171 macro F1 | 93.0%; 0.9257 | 37,147 | 21,104 (-43.19%) | Gate passed; test released |
| LEDGAR test (1,000) | 93.5% accuracy; 0.9299 macro F1 | 92.7%; 0.9223 | 376,088 | 225,573 (-40.02%) | Confirmatory pass |
| CFPB validation (100) | 79.0% accuracy; 0.7838 macro F1 | 72.0%; 0.7053 | 60,514 | 35,247 (-41.75%) | Rejected; test not released |
| SpamAssassin validation (100) | 90.0% accuracy; 0.8996 macro F1 | 86.0%; 0.8580 | 238,077 | 228,359 (-4.08%) | Rejected; test not released |
| QS-OCR/Tobacco validation (100) | 70.0% accuracy; 0.7027 macro F1 | Not run | 1,082,556 | Not run | Baseline nonviable; test not released |
| SROIE LiteParse validation (100) | 0.3436 field F1 | Not run | 49,768 | Not run | Baseline nonviable; test not released |
| RVL-CDIP mirror validation (100) | 50.0% accuracy; 0.4724 macro F1 | Not run | 1,072,199 | Not run | Baseline nonviable; test not released |

On LEDGAR test, the hybrid-minus-NL accuracy difference was -0.8 percentage
points (paired bootstrap 95% interval: -1.6 to 0.0), and the token-reduction
interval was 37.00% to 43.08%. Model calls fell from 1,000 to 589. The 411
command-routed cases account for 146,366 of 150,515 saved tokens (97.24%), so
most savings came from bypassing model calls rather than shortening fallback
prompts. Measured mean latency fell from 0.764 to 0.455 seconds per case. These
are single-machine observations, not hardware-independent latency estimates.

On CFPB validation, the accuracy difference was -7 points (95% interval: -13
to -2), despite a token-reduction interval of 31.30% to 53.14%. NL itself was
one point below the 80% viability floor. The quality gates therefore overruled
the efficiency gain and preserved the 1,000-case test as untouched.

On SpamAssassin validation, accuracy changed from 90% to 86% (paired 95%
interval for the difference: -9 to +1 points) and tokens fell by only 4.08%
(95% interval: 1.02% to 8.50%). It failed both relative gates, so the 1,000-case
test remained untouched. QS-OCR/Tobacco stopped after its 70% NL baseline, and
SROIE stopped after its 0.3436 end-to-end field-F1 baseline. RVL-CDIP likewise
stopped after its 50% natural-language DeepAgent baseline. In all three cases the
absolute viability gate made a hybrid or test run scientifically unnecessary.

## Prepared confirmatory datasets without a completed comparison

| Workflow | Prepared development | Prepared validation | Untouched test | Current status |
| --- | ---: | ---: | ---: | --- |
| SpamAssassin | 100 | 100 | 1,000 | Validation rejected; test untouched |
| QS-OCR-Small / Tobacco3482 | 100 | 100 | 1,000 | NL baseline nonviable; test untouched |
| SROIE | 100 | 100 | 300 | NL baseline nonviable; test untouched |
| RVL-CDIP constrained mirror | 100 | 100 | 369 | NL baseline nonviable; test untouched |

The data-audit pass is not an experiment pass. SROIE has only 300 eligible
official-test receipts after exclusions. RVL uses a capacity-limited mirror and
does not claim a 1,000-case test. No test result is reported for a workflow that
has not first passed its validation gate.

## Prior pilot evidence

The earlier results below use small, predeclared subsets and remain exploratory.
They are retained for transparency but do not replace the confirmatory results.

| Workflow | NL quality | Hybrid quality | NL tokens | Hybrid tokens | Pilot decision |
| --- | ---: | ---: | ---: | ---: | --- |
| LEDGAR contract classification (20) | 85% accuracy; 0.813 macro F1 | 85%; 0.813 | 6,986 | 3,173 (-54.6%) | Accepted |
| CFPB complaint routing (20) | 60% accuracy; 0.583 macro F1 | 60%; 0.583 | 11,724 | 7,479 (-36.2%) | Accepted under pilot rule |
| SpamAssassin email classification (20) | 90% accuracy; 0.899 macro F1 | 85%; 0.847 | 52,250 | 44,270 (-15.3%) | Threshold result; held-out regression |
| SROIE frozen OCR (20) | 0.868 field F1 | 0.864 | 16,295 | 15,109 (-7.3%) | Rejected on validation quality |
| SROIE Tesseract end to end (20) | 0.200 field F1 | 0.178 | 18,487 | 17,338 (-6.2%) | Nonviable OCR baseline; rejected |
| SROIE LiteParse end to end (20) | 0.309 field F1 | 0.297 | 9,889 | 8,696 (-12.1%) | Nonviable validation baseline; rejected |

The historical 32-document RVL-CDIP mirror experiment was also negative. Its
strongest hybrid improved validation accuracy from 81.25% to 87.50% and reduced
tokens by 34.36%, but it remained below that pilot's predeclared 90% quality
floor.

## Interpretation boundary

LEDGAR supports the narrow claim that deterministic SOP steps can bypass model
calls and materially reduce token use while remaining inside a predeclared
quality margin. CFPB is an equally important negative result: lower token use
is not sufficient when quality degrades. The small email and multimodal pilots
show why larger validation gates and OCR viability checks are necessary.

Do not merge classification accuracy, receipt field F1, and OCR error into one
aggregate score. Local-model cost is recorded as $0.00 because no paid API was
used; tokens, model calls, latency, and memory are the measured expense proxies.

## Detailed artifacts

- `ledgar-text-classification/results/confirmatory-*.json`
- `ledgar-text-classification/results/replication-20260902-*.json`
- `cfpb-text-classification/results/confirmatory-validation-*.json`
- `cfpb-text-classification/results/replication-20260902-*.json`
- `spamassassin-email-classification/results/replication-20260902-*.json`
- `datasets/proofs/*-confirmatory.json`
- `document-classification/confirmatory-dataset-proof.json`
- `sroie-receipt-extraction/confirmatory-dataset-proof.json`
- `rvl-cdip-document-classification/confirmatory-dataset-proof.json`
- `rvl-cdip-document-classification/results/confirmatory-validation-*.json`
