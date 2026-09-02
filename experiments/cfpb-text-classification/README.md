# CFPB complaint-routing experiment

This experiment routes public complaint narratives into ten financial-product queues. The official CFPB API response is frozen before selection, avoiding the 1.4 GB mutable bulk export. The dataset preparer freezes 100 balanced cases. A predeclared, deterministic paper subset selects two cases per label (20 total) and assigns 12 development, four validation, and four held-out test cases.

The system prompt, Ollama model and digest, seed, eval CSV, dataset selection, scorer, and harness are frozen across variants. Evolution may change only the SOP and its directly invoked classifier. The maximum is ten iterations; candidate 1 was accepted on development because it preserved accuracy while reducing model calls and tokens.

The hybrid rules were written from the task definition, approved label names,
and development inputs/results only. Validation and test expected labels were
not inspected while authoring or accepting the candidate. Validation confirmed
the acceptance decision; test was run once afterward. The saved latency values
are concurrency-confounded by other local Ollama experiments and must not be
interpreted causally. Token counts and model-call counts come from Ollama's
per-response usage metadata and remain directly comparable.

Complaint narratives and case-level traces stay under ignored `tmp/`. Aggregate run artifacts belong in `results/`. Run `../text-classification/scripts/run_experiment.py` once with `nl/SKILL.md` and once with `hybrid/SKILL.md`; pass `hybrid/classify.py` only for the hybrid run.

## Confirmatory experiment

The prepared confirmatory design supersedes the pilot for future inference:
100 development, 100 validation, and 1,000 untouched complaints, balanced
across ten predeclared product labels. `confirmatory-dataset.json` records
immutable hashes and links to `datasets/proofs/cfpb-confirmatory.json`. All pilot
IDs and normalized complaint contents are excluded from every new split.

The 100-case validation comparison was rejected. NL accuracy was 79% (0.7838
macro F1), below the 80% absolute viability floor, and hybrid accuracy was 72%
(0.7053 macro F1). The hybrid-minus-NL accuracy difference was -7 points, with
a paired 95% bootstrap interval of -13 to -2 points. Although tokens fell from
60,514 to 35,247 (-41.75%; 95% interval: 31.30% to 53.14%), the quality loss
violated both the noninferiority and absolute-quality gates. The 1,000-case test
therefore remains untouched and no confirmatory test claim is made.

Saved validation artifacts are
`results/confirmatory-validation-{nl,hybrid,comparison}.json`. The earlier
20-case result remains exploratory and does not override this rejection.
