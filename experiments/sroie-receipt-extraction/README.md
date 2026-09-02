# SROIE receipt extraction

This experiment compares a natural-language SOP with a hybrid SOP on the same
20 cases drawn from the frozen 100-case SROIE snapshot. It runs in two modes:

- `frozen-ocr`: uses the dataset-supplied words, isolating SOP evolution;
- `end-to-end`: runs local Tesseract before the agent, measuring the deployable
  image-to-JSON pipeline.

Both variants use the same local `qwen3:14b` model and frozen system prompt.
The hybrid SOP may invoke only its own deterministic candidate-extraction
script. No paid API is used. Candidate acceptance requires validation quality
to meet the baseline quality floor and the configured objective to improve.
Evolution is bounded by `max_iterations` (10 in `experiment.json`).

Run:

```bash
python experiments/sroie-receipt-extraction/scripts/run_experiment.py \
  --dataset tmp/datasets/sroie \
  --output experiments/sroie-receipt-extraction/results
```

The output contains case traces, aggregate metrics, immutable hashes, decisions,
and before/after comparisons. Raw dataset images remain under ignored `tmp/`.
`assessment.json` is the canonical final decision: unlike the raw comparison,
it also enforces the minimum viable baseline-quality gate.
