# Three-run optimized variance study, 2026-09-03

This study reran the frozen text-classification skills without regeneration or
evolution. It used paired seeds `20260903`, `20260904`, and `20260905` for
LEDGAR test (1,000 cases), CFPB validation (100), and SpamAssassin validation
(100). The middle seed reversed NL/hybrid order. Every LEDGAR test run is a
replication because those cases were opened previously.

## Frozen runtime and evidence

- Apple M5 Pro, 48 GB; Ollama 0.33.0; `qwen3:14b` digest
  `bdbd181c33f2ed1b31c972991882db3cf4d192569092138a7d29e973cd9debe8`.
- Temperature 0; thinking/streaming off; context 4,096; output cap 128; exact
  JSON schema; retained model; two workers.
- Flash Attention; q8_0 KV cache; one loaded model; two parallel requests.
- Dataset, selection, prompt, SOP, classifier, harness, scorer, and runtime
  hashes were fixed and verified across every run.
- The ignored prepared datasets supplied source records; committed run JSON
  contains IDs, labels, correctness, tokens, latency, routing, and hashes but
  no source text. The automated forbidden-key/common-credential scan passed.

## Results

| Dataset and split | NL accuracy mean (SD) | Hybrid accuracy mean (SD) | Mean NL -> hybrid tokens | Decision in all three pairs |
| --- | ---: | ---: | ---: | --- |
| LEDGAR test | 93.7% (0) | 92.9% (0) | 376,090 -> 225,575.33 (-40.02%) | Pass |
| CFPB validation | 78.0% (0) | 71.0% (0) | 58,372 -> 33,120 (-43.26%) | Reject |
| SpamAssassin validation | 88.0% (0) | 85.0% (0) | 188,384 -> 178,880.67 (-5.04%) | Reject |

Every variant produced identical labels across the three seeds: zero within-NL
and within-hybrid disagreement for all datasets. Routing was also identical.
The deterministic-command/model-fallback splits were 411/589 for LEDGAR,
42/58 for CFPB, and 3/97 for SpamAssassin; each stratum had zero cross-run label
disagreement. Each NL/hybrid pair disagreed on 17, 10, and five cases,
respectively.

The LEDGAR result passed all three gates in all three runs. CFPB passed the
efficiency gate but failed both non-inferiority and the 80% viability floor.
SpamAssassin passed viability and efficiency but failed non-inferiority. These
are repeated positive and rejection/safety outcomes, not evidence of universal
performance. Because both variants observed zero label variation, this study
does not demonstrate a hybrid-specific variance reduction. Three runs are
descriptive and too few for a broad significance claim.

## Artifact map

- `variance-study/preflight.json`: Git, model, runtime, order, and hashes.
- `variance-study/summary.json`: cross-run machine-readable analysis.
- `variance-study/study-manifest.json`: central SHA-256 manifest.
- `{ledgar,cfpb,spamassassin}-*/results/variance-study-20260903/`: raw runs,
  comparisons, exact-command ledgers, logs, local README, and SHA-256 manifest.

The original sequential results and the optimized replications remain separate.
Exact reproduction commands are in `variance-study/README.md`.
