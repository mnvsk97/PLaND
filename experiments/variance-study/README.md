# Three-run text-classification variance study

This study repeats the frozen optimized PLaND runtime for three prespecified
seeds: `20260903`, `20260904`, and `20260905`. Each seed pairs the same natural-
language and hybrid conditions on LEDGAR test (1,000 cases), CFPB validation
(100), and SpamAssassin validation (100). Execution order is NL then hybrid for
the first and third seeds and hybrid then NL for the second seed.

These are replications. LEDGAR's test set was opened previously, and the
original sequential run is not pooled with this two-worker study. The three
runs describe observed variation under one model, machine, data snapshot, and
runtime; they do not establish statistical significance.

## Reproduce

Prepare the frozen datasets as documented in `datasets/README.md`, configure
Ollama as documented in the repository README, and run from the repository
root:

```bash
export OLLAMA_FLASH_ATTENTION=1 OLLAMA_KV_CACHE_TYPE=q8_0
export OLLAMA_NUM_PARALLEL=2 OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_KEEP_ALIVE=-1
python3 experiments/variance-study/run_variance_study.py \
  --dataset-root tmp/confirmatory-datasets
```

The runner validates the model digest, runtime environment, harness hash, and
dataset hashes before work begins. It refuses to overwrite run outputs, writes
atomic checkpoints every 10 cases, skips completed outputs when resumed, and
records the exact command and timestamps for every run in `run-ledger.json`.

After all runs finish:

```bash
python3 experiments/variance-study/aggregate.py \
  --study-dir experiments/ledgar-text-classification/results/variance-study-20260903 \
  --study-dir experiments/cfpb-text-classification/results/variance-study-20260903 \
  --study-dir experiments/spamassassin-email-classification/results/variance-study-20260903 \
  --write-manifests \
  --output experiments/variance-study/summary.json
```

## Artifact map

- `preflight.json`: initial Git, model, runtime, order, and frozen-hash evidence.
- `summary.json`: cross-run accuracy, token, call, latency, prediction-
  disagreement, route-stratified disagreement, and per-run gate results.
- `run_variance_study.py`: prespecified, resumable execution orchestration.
- `aggregate.py`: reusable aggregation, result-content audit, and checksum
  manifest generation.
- `tests/`: unit tests for aggregation and disagreement calculations.
- Each experiment's `results/variance-study-20260903/`: six raw run JSON files,
  three paired comparisons, logs, exact-command ledger, checksum manifest, and
  experiment-local README.

Prepared source records remain under ignored `tmp/`. Committed run JSON files
contain case identifiers, expected/predicted labels, correctness, tokens,
latency, routing source, hashes, and SOP snapshots, but not clause, complaint,
or email text.
