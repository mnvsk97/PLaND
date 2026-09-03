# Enterprise benchmark results

Completed runs used local Ollama `qwen3:14b`, seed `20260902`, frozen evaluation
contracts, and no paid API. Only the SOP package could evolve. The
[`confirmatory protocol`](CONFIRMATORY_PROTOCOL.md) defines the gates.

## Confirmatory results

| Workflow and split | NL quality | Hybrid quality | NL -> hybrid tokens | Decision |
| --- | ---: | ---: | ---: | --- |
| LEDGAR validation (100) | 92.0% accuracy; 0.9171 macro F1 | 93.0%; 0.9257 | 37,147 -> 21,104 (-43.19%) | Pass; test released |
| LEDGAR test (1,000) | 93.5%; 0.9299 | 92.7%; 0.9223 | 376,088 -> 225,573 (-40.02%) | Pass |
| CFPB validation (100) | 79.0%; 0.7838 | 72.0%; 0.7053 | 60,514 -> 35,247 (-41.75%) | Reject; test untouched |
| SpamAssassin validation (100) | 90.0%; 0.8996 | 86.0%; 0.8580 | 238,077 -> 228,359 (-4.08%) | Reject; test untouched |
| QS-OCR/Tobacco validation (100) | 70.0%; 0.7027 | Not run | 1,082,556 -> not run | Baseline nonviable |
| SROIE LiteParse validation (100) | 0.3436 field F1 | Not run | 49,768 -> not run | Baseline nonviable |
| RVL mirror validation (100) | 50.0%; 0.4724 | Not run | 1,072,199 -> not run | Baseline nonviable |

LEDGAR test passed the two-point margin: hybrid minus NL was -0.8 points with a
paired 95% interval of [-1.6, 0.0]. Model calls fell from 1,000 to 589. The 411
command-routed cases contributed 146,366 of 150,515 saved tokens (97.24%);
prompt shortening contributed the rest.

CFPB lost seven accuracy points with interval [-13, -2], and its NL baseline
also missed the 80% floor. SpamAssassin lost four points with interval [-9, +1]
and saved only 4.08% of tokens. Both were rejected. The three image workflows
stopped after nonviable baselines, so no hybrid or test run was warranted.

## Optimized replication

The 2026-09-02 replication used the same model digest with a 4,096-token
context, exact JSON schema, thinking off, retained model, Flash Attention,
q8_0 KV cache, and two parallel requests.

| Workflow and split | NL -> hybrid accuracy | Token reduction | Decision |
| --- | ---: | ---: | --- |
| LEDGAR validation (100) | 93% -> 94% | 43.19% | Pass |
| LEDGAR test (1,000) | 93.7% -> 92.9% | 40.02% | Pass |
| CFPB validation (100) | 78% -> 71% | 43.26% | Reject |
| SpamAssassin validation (100) | 88% -> 84% | 5.04% | Reject |

LEDGAR again bypassed 411 model calls within the quality margin. This is
reproducibility evidence, not a new untouched test. Parallel wall time measures
throughput and cannot be compared directly with sequential timing.

## Three-seed optimized variance study

Three new paired runs used seeds `20260903`, `20260904`, and `20260905`, with
NL/hybrid order reversed for the middle seed. The original sequential run is
not pooled with these two-worker replications.

| Workflow | NL accuracy mean (SD; range) | Hybrid accuracy mean (SD; range) | NL -> hybrid tokens, mean | Cross-run label disagreement | Gate outcome |
| --- | ---: | ---: | ---: | ---: | --- |
| LEDGAR test | 93.7% (0; 93.7-93.7) | 92.9% (0; 92.9-92.9) | 376,090 -> 225,575.33 | 0 NL; 0 hybrid | 3/3 pass |
| CFPB validation | 78.0% (0; 78.0-78.0) | 71.0% (0; 71.0-71.0) | 58,372 -> 33,120 | 0 NL; 0 hybrid | 0/3; reject quality/viability |
| SpamAssassin validation | 88.0% (0; 88.0-88.0) | 85.0% (0; 85.0-85.0) | 188,384 -> 178,880.67 | 0 NL; 0 hybrid | 0/3; reject quality |

Model-call distributions were also invariant: LEDGAR 1,000 -> 589, CFPB
100 -> 58, and SpamAssassin 100 -> 97. Routing never changed across seeds.
Within stable command/model-fallback strata, every dataset had zero cross-run
label disagreement. The paired NL/hybrid disagreements were 17 LEDGAR cases,
10 CFPB cases, and five SpamAssassin cases in each run. Zero observed variation
under this one temperature-zero runtime does not show that the hybrid reduces
variance relative to NL; both variants were at the same zero-disagreement
floor. With only three runs, results are descriptive and do not establish
significance or generalize beyond the frozen model, data, and machine.

The machine-readable analysis is `variance-study/summary.json`. Exact commands,
timestamps, logs, per-case safe traces, comparisons, and SHA-256 manifests are
under each text experiment's `results/variance-study-20260903/` directory.

## Interpretation and artifacts

LEDGAR supports a narrow quality-gated call-bypass claim. Token savings alone
do not establish success, and classification accuracy, receipt field F1, and
OCR error must remain separate metrics. Tokens, calls, latency, and memory are
expense proxies; local service cost is recorded as $0.00.

Detailed JSON is under each experiment's `results/` directory; dataset proofs
are under `datasets/proofs/`. Per-experiment READMEs, JSON summaries, and
existing `RESULTS.md` files retain pilot and dataset-specific context.
