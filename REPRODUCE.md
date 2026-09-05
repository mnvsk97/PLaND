# Reproducing the results

There are three different operations in this repository:

1. **Verify** checks code, tests, hashes, and evidence manifests without using a
   model.
2. **Exact reproduction** reruns an experiment with the recorded input bytes,
   model digest, prompts, runtime, and seed.
3. **Repeat on current data** runs the same code on newly downloaded inputs. It
   is useful, but it is not expected to reproduce the paper's exact numbers.

## What is reproducible from a fresh clone?

| Dataset | Code and results included | Public source can be prepared | Extra requirement for exact reproduction |
|---|---|---|---|
| LEDGAR | Yes | Yes | Locked source files and model digest |
| SpamAssassin | Yes | Yes | Locked source archives and model digest |
| CFPB | Yes | Yes, from the live API | Frozen `complaints-api.json` snapshot |
| QS-OCR/Tobacco3482 | Yes | Yes | Locked archive, label audit, and local OCR setup |
| SROIE | Yes | Yes, as a new condition | Frozen `rows.json` snapshot |
| RVL-CDIP mirror | Yes | Yes | Pinned mirror revision; a byte-repeat was not recorded |

Raw benchmark records are intentionally outside Git. Their required locations,
URLs, byte sizes, revisions, and hashes are recorded in
[`datasets/sources.lock.json`](datasets/sources.lock.json).

## 1. Install and verify

Requirements: Git, Python 3.11–3.14, `uv`, and Ollama for model runs.
Document-image experiments additionally require their documented OCR runtime.

```bash
git clone https://github.com/mnvsk97/PLaND.git
cd PLaND
make setup
make verify
```

Expected final line begins with `PASS:` and reports the test directories and
verified manifest files.

`pyproject.toml` declares the direct Python dependencies. `uv.lock` pins the
complete resolved dependency graph. They are needed so a new user does not have
to guess package versions; neither file contains experiment logic.

The `Makefile` is only a short command index for setup, verification, paper
builds, and the two repeated studies. The actual logic remains in the Python
scripts. Run `make help` to see the five targets or `make -n TARGET` to print a
target without executing it.

## 2. Freeze the model runtime

The reported text runs used Ollama 0.33.0 and `qwen3:14b` with digest:

```text
bdbd181c33f2ed1b31c972991882db3cf4d192569092138a7d29e973cd9debe8
```

Check the installed model before running:

```bash
ollama show qwen3:14b
export OLLAMA_FLASH_ATTENTION=1 OLLAMA_KV_CACHE_TYPE=q8_0
export OLLAMA_NUM_PARALLEL=2 OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_KEEP_ALIVE=-1
```

`ollama pull qwen3:14b` today may resolve to different model bytes. If the
digest differs, treat the output as a new replication rather than an exact
reproduction.

## 3. Prepare the text datasets

Create the pilot selections first because the confirmatory selections exclude
them. LEDGAR and SpamAssassin can be downloaded by the preparer:

```bash
for dataset in ledgar spamassassin; do
  uv run python datasets/scripts/prepare_data.py "$dataset" \
    --output "tmp/paper-datasets/$dataset"
  uv run python datasets/scripts/prepare_data.py "$dataset" \
    --output "tmp/confirmatory-datasets/$dataset" \
    --exclude-dataset "tmp/paper-datasets/$dataset" \
    --development-cases 100 --validation-cases 100 --test-cases 1000
done
```

For an exact CFPB reconstruction, place the frozen API response at
`tmp/source-snapshots/cfpb/complaints-api.json`, verify its hash against the
source lock, and pass it explicitly to both preparations:

```bash
uv run python datasets/scripts/prepare_data.py cfpb \
  --source tmp/source-snapshots/cfpb/complaints-api.json \
  --output tmp/paper-datasets/cfpb
uv run python datasets/scripts/prepare_data.py cfpb \
  --source tmp/source-snapshots/cfpb/complaints-api.json \
  --output tmp/confirmatory-datasets/cfpb \
  --exclude-dataset tmp/paper-datasets/cfpb \
  --development-cases 100 --validation-cases 100 --test-cases 1000
```

The quality-first datasets require the three locked raw-source directories and
the three confirmatory selections:

```bash
uv run python datasets/scripts/prepare_quality_first.py \
  --source-root tmp/source-snapshots \
  --confirmatory-root tmp/confirmatory-datasets \
  --output tmp/quality-first-datasets
```

See [`datasets/README.md`](datasets/README.md) for audit commands and the
document-dataset protocols.

## 4. Run the repeated text studies

Use a fresh output directory. The committed result directories are evidence,
not scratch space.

```bash
make reproduce-text-replications \
  CONFIRMATORY_DATASET_ROOT=tmp/confirmatory-datasets

make reproduce-quality-first \
  QUALITY_FIRST_DATASET_ROOT=tmp/quality-first-datasets
```

Both commands write under ignored `tmp/reproduction-runs/`. The first uses
seeds 20260903–20260905. The quality-first study uses seeds
20260906–20260908. A seed controls a prespecified paired run; it is not a claim
that the dataset was randomly reselected each time.

## 5. Run the document baselines

Dataset construction is documented next to each experiment:

- [`experiments/document-classification/DATASET.md`](experiments/document-classification/DATASET.md)
- [`experiments/sroie-receipt-extraction/README.md`](experiments/sroie-receipt-extraction/README.md)
- [`experiments/rvl-cdip-document-classification/DATASET.md`](experiments/rvl-cdip-document-classification/DATASET.md)

Once those prepared directories exist, the reported validation baselines use:

```bash
mkdir -p tmp/reproduction-runs

uv run python experiments/document-classification/scripts/run_evals.py \
  --agent experiments/document-classification/schema-v2/nl-baseline \
  --evals tmp/paper-datasets/qs-ocr-confirmatory/evals.csv \
  --datasource-root tmp/paper-datasets/qs-ocr-confirmatory/documents \
  --split validation --model qwen3:14b --seed 20260902 \
  --output tmp/reproduction-runs/qs-ocr-validation-nl.json

uv run python experiments/document-classification/scripts/run_evals.py \
  --agent experiments/rvl-cdip-document-classification/schema-v2/nl-baseline \
  --evals tmp/paper-datasets/rvl-cdip-confirmatory/evals.csv \
  --datasource-root tmp/paper-datasets/rvl-cdip-confirmatory/documents \
  --split validation --model qwen3:14b --seed 20260902 \
  --output tmp/reproduction-runs/rvl-validation-nl.json

uv run python experiments/sroie-receipt-extraction/scripts/run_experiment.py \
  --dataset tmp/paper-datasets/sroie-confirmatory \
  --split validation --mode end-to-end --variant nl-baseline \
  --output tmp/reproduction-runs/sroie-validation
```

These baselines stopped at the prespecified viability gate, so no hybrid or
test run should be launched merely to force a favorable result.

## Reading a reproduction

Compare quality, predictions, routing, model calls, and tokens against the
committed JSON and summaries linked from [`RESULTS.md`](RESULTS.md). Latency is
hardware-dependent. Any mismatch in dataset hash, SOP hash, model digest, or
runtime condition must be reported as a different condition rather than pooled
with the paper result.
