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
