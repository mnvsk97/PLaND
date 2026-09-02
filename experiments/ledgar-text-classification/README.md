# LEDGAR text-classification experiment

This experiment classifies public contract provisions into ten common provision types. The dataset preparer freezes 100 balanced cases. A predeclared, deterministic paper subset selects two cases per label (20 total) and assigns 12 development, four validation, and four held-out test cases.

The system prompt, Ollama model and digest, seed, eval CSV, dataset selection, scorer, and harness are frozen across variants. Evolution may change only the SOP and its directly invoked classifier. The maximum is ten iterations; candidate 1 was accepted on development because it preserved accuracy while reducing model calls and tokens.

The hybrid rules were written from the task definition, approved label names,
and development inputs/results only. Validation and test expected labels were
not inspected while authoring or accepting the candidate. Validation confirmed
the acceptance decision; test was run once afterward. The saved latency values
are concurrency-confounded by other local Ollama experiments and must not be
interpreted causally. Token counts and model-call counts come from Ollama's
per-response usage metadata and remain directly comparable.

Raw source documents, case inputs, and case-level traces stay under ignored `tmp/`. Aggregate run artifacts belong in `results/`. Run `../text-classification/scripts/run_experiment.py` once with `nl/SKILL.md` and once with `hybrid/SKILL.md`; pass `hybrid/classify.py` only for the hybrid run.

## Confirmatory experiment

The confirmatory design supersedes the pilot for inference:
100 development, 100 validation, and 1,000 untouched test clauses, balanced
across ten labels. `confirmatory-dataset.json` records immutable hashes and
links to `datasets/proofs/ledgar-confirmatory.json`. All pilot IDs and normalized
contents are excluded. Development, validation, and test remain inside the
official LexGLUE train, validation, and test boundaries respectively.

The 100-case validation comparison passed the prespecified local gate: NL accuracy
was 92% and hybrid accuracy was 93% (paired accuracy-difference 95% bootstrap
interval: -2 to +5 percentage points). Tokens fell from 37,147 to 21,104, a
43.19% reduction (95% interval: 33.61% to 53.35%). The held-out test was then
released once.

On the 1,000-case test, NL reached 93.5% accuracy and 0.9299 macro F1; hybrid
reached 92.7% accuracy and 0.9223 macro F1. The -0.8-point accuracy difference
had a paired 95% bootstrap interval of -1.6 to 0.0 points, within the -2-point
noninferiority margin. Tokens fell from 376,088 to 225,573 (-40.02%; 95%
interval: 37.00% to 43.08%), model calls fell from 1,000 to 589, and measured
mean latency fell from 0.764 to 0.455 seconds per case. The result passed the
relative-quality, absolute-quality, and token-reduction gates. Latency is a
single-machine measurement, not a hardware-independent estimate.

Saved artifacts are `results/confirmatory-validation-{nl,hybrid,comparison}.json`
and `results/confirmatory-test-{nl,hybrid,comparison}.json`.
