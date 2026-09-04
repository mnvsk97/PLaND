# Generic quality-first validation replications

This prospective study applies one dataset-independent evolver policy to three
text-classification tasks. Each task retains its own labels, system prompt,
deterministic command, and scorer configuration. The shared policy preserves
the complete NL path as fallback, mines command changes only from development,
and requires task-local quality guardrails before expense savings count.

New prepared datasets exclude all 1,200 cases from each prior confirmatory
selection. Their validation splits contain 500 cases per dataset. The test
splits remain closed during these three paired validation replications.

Run with the frozen Ollama environment:

```bash
export OLLAMA_FLASH_ATTENTION=1 OLLAMA_KV_CACHE_TYPE=q8_0
export OLLAMA_NUM_PARALLEL=2 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_KEEP_ALIVE=-1
python3 experiments/quality-first-replications/run_study.py \
  --dataset-root tmp/quality-first-datasets
```

The middle replication reverses NL/candidate order. Outputs, logs, the exact
command ledger, and comparisons are written under each task's
`results/quality-first-validation-20260903/` directory. A failed validation
gate is retained as rejection evidence and does not release the test split.

## Results

All three seeds produced identical predictions and token counts for both
variants on every dataset. The observed across-run accuracy SD and range are
therefore zero under this frozen greedy-decoding condition. That is a narrow
reproducibility result, not proof that other models, sampling settings, data,
or runtime conditions have zero variance.

| Dataset | NL accuracy | Quality-first accuracy | Difference | Paired 95% interval | Token reduction | Command route |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| LEDGAR | 93.6% | 92.8% | -0.8 pp | [-1.6, -0.2] pp | 8.36% | 82/500 at 98.78% precision |
| CFPB | 74.8% | 73.8% | -1.0 pp | [-2.4, +0.2] pp | -2.25% | 12/500 at 100% precision |
| SpamAssassin | 90.2% | 89.0% | -1.2 pp | [-2.2, -0.4] pp | -0.59% | 3/500 at 100% precision |

Negative token reduction means the candidate consumed more tokens. Every
candidate failed the frozen release policy in all three replications. LEDGAR
saved enough tokens but regressed quality, missed the paired lower-bound and
per-label guardrails, and had command precision below 99%. CFPB also missed
the 80% absolute-quality floor and increased tokens. SpamAssassin preserved
absolute viability but regressed quality and increased tokens. No held-out
test split was opened.

The evidence does not support repeatedly asking the evolver to "increase
accuracy" on these same validation cases. That would adapt to validation and
bias the estimate. A next candidate should diagnose failure slices using only
development data, freeze a new generic transformation, and use a fresh
validation boundary.

The machine-readable cross-study aggregate and safety audit are in
`summary.json`; `study-manifest.json` checksums the complete study payload.
