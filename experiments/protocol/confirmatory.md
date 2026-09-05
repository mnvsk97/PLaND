# PLaND confirmatory protocol

This local, non-registered protocol was fixed before expanded held-out tests.
It evaluates pilot-selected SOPs without using expanded test outcomes to write
new rules.

## Design

- Local Ollama `qwen3:14b`; temperature 0; reasoning off.
- Seed `20260902` for text; previously frozen seeds for multimodal harnesses.
- At most ten evolution attempts; none after the pilot SOP is frozen.
- Text: 100 development, 100 validation, 1,000 test cases.
- SROIE: 100 development, 100 validation, and 300 eligible official-test
  receipts after pilot and duplicate exclusions.
- RVL mirror: 100 development, 100 validation, and all 369 eligible test images.
- Exclude pilots and preserve official source splits when available.
- Keep raw licensed data local; commit proofs, hashes, counts, aggregate results,
  and safe traces.

## Frozen boundary

NL and hybrid runs must match on model/digest, system prompt, normalized harness,
evaluation inputs and outputs, scorer, datasource snapshot, seed, runtime, and
permissions. Only the workflow package may differ: `SKILL.md`, direct
references, invoked Python/Bash scripts or tools, and approved dependencies.

## Gates

Validation releases test only when:

1. All frozen fingerprints match.
2. The paired 95% bootstrap lower bound for `accuracy_hybrid - accuracy_NL` is
   at least `-0.02`.
3. Token reduction is at least 5% with a positive paired 95% lower bound.
4. Both classification accuracies are at least 0.80; receipt extraction instead
   requires field F1 of at least 0.50.

Checks 1-3 support the relative PLaND claim; check 4 prevents an efficient but
nonviable baseline from releasing test.

## Statistics and timing

Report accuracy, macro F1, model calls, tokens, latency, direct service cost,
Wilson accuracy intervals, paired bootstrap intervals, and exact McNemar tests.
Use 5,000 resamples with seed `20260902`.

Original confirmatory runs were sequential. The optimized replication uses two
parallel requests, so its wall time measures throughput and is not directly
comparable. Local Ollama has no per-call service charge; tokens and calls remain
portable expense proxies. Setup and commands are in the repository
[`README.md`](../../README.md).

## Three-run variance extension

The 2026-09-03 variance study repeats the frozen optimized text runtime with
seeds `20260903`, `20260904`, and `20260905`. The same seed is used within each
NL/hybrid pair. Order is NL then hybrid for the first and third seeds and hybrid
then NL for the second. LEDGAR uses the already-opened 1,000-case test split;
CFPB and SpamAssassin remain on their 100-case validation splits. Every LEDGAR
evaluation is a replication, not an untouched test.

The original sequential result and the optimized runs are reported separately,
not pooled. Three runs support descriptive means, sample standard deviations,
ranges, case-level agreement, and pairwise disagreement, but not a significance
or general-model claim. The exact commands, environment, hashes, checkpoints,
logs, raw safe result payloads, comparisons, and manifests are mapped in
[`variance-study/README.md`](../variance-study/README.md).
