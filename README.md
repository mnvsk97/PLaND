# PLaND

Path to Least Non Determinism (PLaND) is a methodology for moving stable SOP
steps from natural language into references, Python, or Bash while retaining
model judgment. Freeze the evaluation contract, change only the skill package,
and accept a candidate only when quality and expense gates pass.

Across three new 1,000-case LEDGAR replications, the accepted hybrid passed the
quality and efficiency gates every time, held accuracy at 92.9% versus 93.7%
NL, reduced tokens by 40.02%, and replaced 411 model calls with commands. Both
variants had zero label disagreement across the three seeds. CFPB and
SpamAssassin reproduced their quality-gate rejections; three document-image
baselines remain nonviable feasibility cases.

## Repository map

- [`skills/generate-initial-version`](skills/generate-initial-version/): initial
  open-ended agent and natural-language SOP.
- [`skills/pland-evolver`](skills/pland-evolver/): bounded, evaluation-gated SOP
  changes.
- [`datasets`](datasets/): preparation, proofs, hashes, and audits.
- [`experiments`](experiments/): runners, SOPs, decisions, and results.
- [`experiments/variance-study`](experiments/variance-study/): three-seed
  commands, manifests, aggregation code, and cross-run results.
- [`paper/PAPER.md`](paper/PAPER.md): manuscript source.
- [`output/paper`](output/paper/): generated MD, PDF, DOCX, and HTML.

## Quick start

Prerequisites: Git, Python 3.11--3.14, [uv](https://docs.astral.sh/uv/), and
[Ollama](https://ollama.com/download). LibreOffice is required only when
rebuilding every paper format. The root `uv.lock` pins the complete Python
environment used by the tests, paper builders, and experiment runners.

```bash
git clone https://github.com/mnvsk97/PLaND.git
cd PLaND
make setup
make verify
```

`make verify` is offline: it runs every tracked unit-test suite, checks the
committed evidence and paper/arXiv manifests, and validates the final-paper
recipe without invoking Ollama or rewriting checked-in outputs.

Prepare the same LEDGAR pilot-exclusion and confirmatory selections used by the
study, then use the validation commands below:

```bash
python datasets/scripts/prepare_data.py ledgar \
  --output tmp/paper-datasets/ledgar
python datasets/scripts/prepare_data.py ledgar \
  --output tmp/confirmatory-datasets/ledgar \
  --exclude-dataset tmp/paper-datasets/ledgar \
  --development-cases 100 --validation-cases 100 --test-cases 1000
```

Preparation downloads public data. Use `--source PATH` for an existing local
copy. Dataset rules and proof commands are in [`datasets/README.md`](datasets/README.md).

## Optimized Ollama and Qwen setup

The replication used Ollama 0.33.0, `qwen3:14b`, 4,096-token requests, no
thinking, temperature 0, an exact JSON schema, and two workers. Keep the model
digest fixed within a comparison.

<details>
<summary>On macOS with the Homebrew service</summary>

<br>

```bash
ollama pull qwen3:14b
launchctl setenv OLLAMA_FLASH_ATTENTION 1
launchctl setenv OLLAMA_KV_CACHE_TYPE q8_0
launchctl setenv OLLAMA_NUM_PARALLEL 2
launchctl setenv OLLAMA_MAX_LOADED_MODELS 1
launchctl setenv OLLAMA_KEEP_ALIVE -1
brew services restart ollama
```

</details>

<details>
<summary>On Linux</summary>

<br>

Add this with `systemctl edit ollama.service`, then run
`sudo systemctl daemon-reload && sudo systemctl restart ollama`:

```ini
[Service]
Environment="OLLAMA_FLASH_ATTENTION=1"
Environment="OLLAMA_KV_CACHE_TYPE=q8_0"
Environment="OLLAMA_NUM_PARALLEL=2"
Environment="OLLAMA_MAX_LOADED_MODELS=1"
Environment="OLLAMA_KEEP_ALIVE=-1"
```

</details>

Preload and verify:

```bash
curl -fsS http://127.0.0.1:11434/api/generate \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen3:14b","keep_alive":-1,"options":{"num_ctx":4096}}' \
  >/dev/null
ollama ps
ollama show qwen3:14b
```

Two parallel 4K requests allocate an 8K server context. Use one worker on
lower-memory machines. Remove persistent macOS values with `launchctl unsetenv
VARIABLE`; on Linux, remove the service override. Restart Ollama afterward.

## Run LEDGAR validation

Assuming data is at `tmp/confirmatory-datasets/ledgar`:

```bash
export OLLAMA_FLASH_ATTENTION=1 OLLAMA_KV_CACHE_TYPE=q8_0
export OLLAMA_NUM_PARALLEL=2 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_KEEP_ALIVE=-1

python experiments/text-classification/scripts/run_experiment.py \
  --dataset tmp/confirmatory-datasets/ledgar --split validation \
  --system-prompt experiments/ledgar-text-classification/system-prompt.md \
  --sop experiments/ledgar-text-classification/nl/SKILL.md --workers 2 \
  --output tmp/ledgar-validation-nl.json

python experiments/text-classification/scripts/run_experiment.py \
  --dataset tmp/confirmatory-datasets/ledgar --split validation \
  --system-prompt experiments/ledgar-text-classification/system-prompt.md \
  --sop experiments/ledgar-text-classification/hybrid/SKILL.md \
  --classifier experiments/ledgar-text-classification/hybrid/classify.py \
  --workers 2 --output tmp/ledgar-validation-hybrid.json

python experiments/text-classification/scripts/compare.py \
  --nl tmp/ledgar-validation-nl.json \
  --hybrid tmp/ledgar-validation-hybrid.json --minimum-accuracy 0.80 \
  --output tmp/ledgar-validation-comparison.json
```

Do not open a test split unless validation passes. Runs retain runtime settings,
artifact hashes, usage, timing, outputs, and checkpoints; comparisons preserve
variant SOP hashes and reject runtime mismatches.

## Tests, paper, and full experiment reproduction

```bash
make verify
make reproduce-paper

# Requires both prepared dataset roots and the frozen Ollama model/runtime.
make reproduce-experiments \
  CONFIRMATORY_DATASET_ROOT=tmp/confirmatory-datasets \
  QUALITY_FIRST_DATASET_ROOT=tmp/quality-first-datasets
```

Full experiment reproduction writes new runs and aggregate summaries under
ignored `tmp/reproduction-runs/`; it never treats the committed result files as
new runs. Override `REPRODUCTION_ROOT` to choose another empty destination.

See [`paper/README.md`](paper/README.md) and the latest
[`recollection`](experiments/RECOLLECTION_2026-09-02.md). Raw licensed or
sensitive data stays local; the repository keeps source references, selection
rules, proofs, hashes, aggregate results, and reproduction code. Repeated
LEDGAR test runs are replications, not new untouched tests.
