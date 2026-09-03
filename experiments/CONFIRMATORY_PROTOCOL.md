# PLaND confirmatory protocol

This local protocol was specified before the expanded held-out tests were run.
It was not registered in an external registry. It
evaluates the SOPs selected by the earlier pilot; it does not use expanded test
outcomes to write new rules.

## Design

- Model: local Ollama `qwen3:14b`, temperature 0, reasoning disabled.
- Model seed: `20260902` for text classification and the previously frozen seed
  for each multimodal harness.
- Maximum evolution attempts: 10. No new attempt is made after the pilot SOP is
  frozen.
- Classification datasets: 100 development, 100 validation, and 1,000 held-out
  test cases.
- SROIE: 100 development and 100 validation cases from the official training
  split, plus the 300 official-test receipts left after removing pilot cases,
  cross-ID pilot-image duplicates,
  and exact duplicates.
- RVL-CDIP mirror: 100 development, 100 validation, and all 369 usable,
  untouched official-test images available after pilot and empty-OCR exclusions.
- Prior pilot cases are excluded from the expanded selections. Official source
  split boundaries are preserved where the upstream dataset supplies them.
- Raw licensed data stays in ignored local storage. Check-in-safe manifests,
  hashes, counts, audit outcomes, aggregate results, and de-identified traces
  are retained in the repository.

## Frozen boundary

Across the natural-language baseline and hybrid candidate, the model and
digest, system prompt, harness, eval inputs and expected outputs, scorer,
datasource snapshot, seed, model settings, and execution permissions must have
identical fingerprints. The comparison is invalid if any invariant differs.

The only permitted differences are inside the workflow SOP package:
`SKILL.md`, directly referenced instruction files, directly invoked tools and
Python or Bash scripts, and approved dependencies required by those scripts.

## Stage gates

The selected pilot candidate is first evaluated on the new validation split.
The held-out test is run only when all of these checks pass:

1. Frozen fingerprints match exactly.
2. The lower bound of the paired 95% bootstrap interval for
   `accuracy_hybrid - accuracy_NL` is at least `-0.02`.
3. Token reduction is at least 5%, and the lower bound of its paired 95%
   bootstrap interval is above zero.
4. Classification accuracy is at least 0.80 for both conditions. Structured
   receipt extraction uses a field-F1 floor of 0.50.

The first three checks test the relative PLaND claim. The fourth is a separate
absolute viability check. A candidate can preserve an inadequate baseline; that
is not a deployable success and does not justify spending the untouched test
set.

## Statistics

Classification comparisons report accuracy, macro-F1, model calls, tokens,
latency, direct model-service cost, Wilson 95% intervals for each accuracy,
paired bootstrap 95% intervals for the accuracy difference and token reduction,
and an exact McNemar test. Bootstrap calculations use 5,000 resamples and seed
`20260902`.

Original confirmatory latency is recorded from sequential local runs. The
post-change replication uses two parallel requests and stores the full runtime
configuration; its wall time measures throughput and is not compared directly
with sequential latency. Local Ollama has zero direct per-call service cost;
tokens and model calls are retained so readers can map the result to their own
pricing and energy assumptions. Copy-paste Ollama configuration and execution
instructions are in the repository `README.md`.
