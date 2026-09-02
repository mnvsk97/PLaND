# PLaND tau-retail experiment

This experiment compares a natural-language SOP with a hybrid SOP on a frozen,
deterministic 20-case subset of the 100 prepared tau-retail cases. The retail
database and tools run locally. Both agent and user simulation use local Ollama
`qwen3:14b`; no paid API is called.

The 20 cases are selected before any run: the first 12 development, first four
validation, and first four test records in the frozen `evals.csv`. This smaller
paper subset is necessary because the initial one-case local smoke run took
245.85 seconds and reached its step limit; a think-disabled smoke still took
137.79 seconds. The paper run therefore applies the same eight-step and
60-second per-case bounds to both candidates. All 100 cases remain frozen for
future higher-throughput replication.

Run:

```bash
python experiments/tau-retail/run_experiment.py \
  --dataset experiments/tau-retail/dataset \
  --tau-repo tmp/tau2-bench
```

The runner rejects mismatched tau revisions, dataset seeds, and source
revisions. It saves the frozen invariant contract, complete traces, and metrics
for task success, final-state correctness, tokens, latency, zero paid-API cost,
tool calls, peak child-process RSS, and SOP representation under `results/`.

Only the SOP package differs. The model and digest, base system prompt, harness,
evaluation data, expected outputs, final-state scorer, source snapshots, seed,
and execution permissions are identical across candidates. Evolution is capped
at ten iterations; this run contains the baseline and first hybrid candidate.
