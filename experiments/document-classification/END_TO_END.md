# End-to-end reproduction

This experiment is a 20-case proof-of-concept: 10 development cases and 10
validation cases. It does not contain a third held-out split. Read
[`DATASET.md`](DATASET.md) before using the data and [`RESULTS.md`](RESULTS.md)
before interpreting the measurements.

The completed frozen-prompt NL-versus-hybrid follow-up is documented in
[`schema-v2/RESULTS.md`](schema-v2/RESULTS.md). Its safe machine-readable
development and validation comparisons are stored under `schema-v2/comparisons/`.

## Runtime

- Ollama 0.33.0
- Model: `qwen3:14b`
- Digest: `bdbd181c33f2ed1b31c972991882db3cf4d192569092138a7d29e973cd9debe8`
- Temperature: 0
- Seed: 42
- Reasoning: disabled

The local environment used for the recorded run is
`tmp/document-classification-venv`. Raw OCR and evaluation rows remain under
`tmp/` and are intentionally not committed.

## 1. Generate an initial agent

```bash
python3 skills/generate-initial-version/scripts/generate.py \
  --workflow document-classification \
  --requirements experiments/document-classification/requirements.md \
  --sources tmp/document-classification-subset/documents \
  --evals tmp/document-classification-subset/evals.csv \
  --output <initial-agent-directory> \
  --model-provider ollama
```

Replace the generic generated SOP steps with the shortest workflow justified
by the requirements. The frozen initial SOP is at
`initial-agent/skills/document-classification/SKILL.md`.

## 2. Run isolated evaluations

```bash
python3 experiments/document-classification/scripts/run_evals.py \
  --agent <agent-directory>/agent.py \
  --evals tmp/document-classification-subset/evals.csv \
  --split development \
  --model qwen3:14b \
  --seed 42 \
  --output <development-run.json>
```

The runner hides expected output and reasoning from the agent, starts each case
from isolated message state, and records the complete local trace, exact output,
tokens, latency, errors, model digest, seed, aggregate score, and an immutable
snapshot and hash of the evaluated SOP with representation counts.

## 3. Gate a candidate

```bash
python3 skills/pland-evolver/scripts/assess_candidate.py \
  --baseline-development <baseline-development.json> \
  --candidate-development <candidate-development.json> \
  --candidate <candidate-name> \
  --hypothesis <bounded-hypothesis> \
  --iteration <one-based-iteration> \
  --max-iterations 10 \
  --target-accuracy 0.90 \
  --max-validation-latency-ratio 2.0 \
  --output <development-decision.json>
```

Only a result of `eligible_for_validation` permits the validation run. Invoke
the assessor again with `--baseline-validation` and `--candidate-validation`;
only `accept` changes the accepted agent.

For a true hybrid SOP containing at least one explicitly marked command step,
save the before/after measurement artifact:

```bash
python3 skills/pland-evolver/scripts/compare_variants.py \
  --natural-language-run <initial-run.json> \
  --hybrid-run <accepted-hybrid-run.json> \
  --output <nl-vs-hybrid-comparison.json>
```

## Verified behavior

On 2026-09-01, both reusable skills passed the skill validator and all seven
repository unit tests passed. A freshly generated agent compiled, imported,
loaded its SOP, and read a real datasource through the approved tool. That
baseline classified development email `2085319449` as `letter`; the accepted
evolved agent classified the same input as `email`. Re-running the deterministic
candidate assessor over the frozen full-run artifacts returned `accept` with no
failed checks. The full initial and accepted development/validation metrics are
in [`RESULTS.md`](RESULTS.md).
