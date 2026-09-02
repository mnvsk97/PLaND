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
