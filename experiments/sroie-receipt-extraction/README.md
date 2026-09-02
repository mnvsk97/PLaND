# SROIE receipt extraction

This experiment compares a natural-language SOP with a hybrid SOP on the same
20 cases drawn from the frozen 100-case SROIE snapshot. It runs in two modes:

- `frozen-ocr`: uses the dataset-supplied words, isolating SOP evolution;
- `end-to-end`: runs pinned local LiteParse before the agent, measuring the
  deployable image-to-JSON pipeline. LiteParse's default local OCR engine is
  Tesseract, while LiteParse supplies deterministic structured text items.

Both variants use the same local `qwen3:14b` model and frozen system prompt.
The hybrid SOP may invoke only its own deterministic candidate-extraction
script. No paid API is used. The LiteParse version and OCR settings are frozen
as experiment invariants. Candidate acceptance requires validation quality
to meet the baseline quality floor and the configured objective to improve.
Evolution is bounded by `max_iterations` (10 in `experiment.json`).

Run:

```bash
python -m venv experiments/sroie-receipt-extraction/.venv
experiments/sroie-receipt-extraction/.venv/bin/python -m pip install \
  experiments/sroie-receipt-extraction
PATH="experiments/sroie-receipt-extraction/.venv/bin:$PATH" \
experiments/sroie-receipt-extraction/.venv/bin/python \
  experiments/sroie-receipt-extraction/scripts/run_experiment.py \
  --dataset tmp/datasets/sroie \
  --output experiments/sroie-receipt-extraction/results/liteparse
```

Then apply the prespecified local viability gate:

```bash
experiments/sroie-receipt-extraction/.venv/bin/python \
  experiments/sroie-receipt-extraction/scripts/assess_results.py \
  --results experiments/sroie-receipt-extraction/results/liteparse
```

The output contains case traces, aggregate metrics, immutable hashes, decisions,
and before/after comparisons. Raw dataset images remain under ignored `tmp/`.
`assessment.json` is the canonical final decision: unlike the raw comparison,
it also enforces the minimum viable baseline-quality gate.

## Confirmatory dataset status

The expanded data contains 100 development and 100 validation receipts selected
from the official train split, plus 300 eligible official-test receipts after
prior-pilot and exact-image exclusions. The committed
`confirmatory-dataset-proof.json` passes ID separation, file and image hashes,
expected-output leakage, official-boundary, pilot-overlap, duplicate-image, and
byte-repeat checks.

The confirmatory end-to-end NL baseline is complete on all 100 validation
receipts. Field F1 was `0.344`, below the prespecified local `0.50` viability floor;
OCR word error rate was `0.676`. The experiment therefore stopped before the
hybrid validation run, and the corrected 300-case test remained untouched. The committed
result is an aggregate, deidentified publication view; its `raw_run_sha256`
fingerprints the complete local trace retained under ignored `tmp/`. The
20-case measurements in `RESULTS.md` remain pilot results.
