# PLaND

Path to Least Non-Determinism (PLaND) is a methodology for replacing stable
model-mediated SOP steps with deterministic references or scripts while
preserving measured quality.

## Paper

The submitted paper is available in four formats:

- [PDF](paper/PLaND.pdf)
- [Word](paper/PLaND.docx)
- [HTML](paper/PLaND.html)
- [Markdown](paper/PLaND.md)

The three figures used by the paper are in [`paper/figures/`](paper/figures/).

## Repository structure

```text
PLaND/
├── paper/          paper formats and figures
├── experiments/    experiment SOPs, reproduction scripts, and results
├── datasets/       dataset preparation, source locks, and audit scripts
├── skills/         the two PLaND methodology skills
└── reproduce/      locked Python environment and repository verification
```

## Reported experiments

| Experiment | Paper result |
|---|---|
| LEDGAR | Hybrid passed the original validation and 1,000-case test gates; test tokens fell 40.02% |
| CFPB | Hybrid rejected on validation |
| SpamAssassin | Hybrid rejected on validation |
| QS-OCR/Tobacco3482 | Natural-language baseline was below the viability floor |
| SROIE | End-to-end extraction baseline was below the viability floor |
| RVL-CDIP mirror | Natural-language baseline was below the viability floor |
| Three-seed replications | LEDGAR passed 3/3; CFPB and SpamAssassin were rejected 3/3 |
| Fresh quality-first validation | LEDGAR, CFPB, and SpamAssassin candidates were all rejected |

The corresponding code and machine-readable results are under:

```text
experiments/
├── protocol/                       frozen confirmatory protocol and runtime
├── ledgar-text-classification/
├── cfpb-text-classification/
├── spamassassin-email-classification/
├── document-classification/
├── sroie-receipt-extraction/
├── rvl-cdip-document-classification/
├── variance-study/
├── quality-first-replications/
└── text-classification/          shared text runner and scorer
```

## Verify the repository

Requirements: Git, Python 3.11–3.14, and
[`uv`](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/mnvsk97/PLaND.git
cd PLaND
uv sync --project reproduce --frozen
reproduce/.venv/bin/python reproduce/verify.py
```

`reproduce/pyproject.toml` lists the Python dependencies and
`reproduce/uv.lock` freezes their exact resolved versions. They are grouped
under `reproduce/` because they exist only to run and verify the experiments.

## Reproduction status

| Goal | Status |
|---|---|
| Verify the committed code, results, manifests, and paper files | Fully reproducible from a clean clone |
| Rerun LEDGAR and SpamAssassin on the locked public source files | Reproducible when the recorded Ollama model digest is available |
| Exactly rerun CFPB | Requires the frozen `complaints-api.json` snapshot, which is not redistributed |
| Exactly rerun SROIE | Requires the frozen `rows.json` snapshot, which is not redistributed |
| Rerun with current CFPB, SROIE, or model data | Supported, but must be reported as a new experimental condition |

Therefore, the public repository is sufficient to verify all reported evidence,
but it is not sufficient by itself to regenerate every historical number. Exact
regeneration additionally requires the recorded raw-input bytes and
`qwen3:14b` model digest. This limitation must be disclosed when describing the
repository as reproducible.

## Prepare datasets

Dataset URLs, revisions, file sizes, SHA-256 hashes, and redistribution limits
are recorded in [`datasets/sources.lock.json`](datasets/sources.lock.json).
Preparation and audit commands are in [`datasets/README.md`](datasets/README.md).

Raw benchmark records are not committed. LEDGAR and SpamAssassin can be rebuilt
from the locked public files. Exact CFPB and SROIE reconstruction requires the
frozen local snapshots recorded by the source lock; using current upstream data
is a new experimental condition.

## Reproduce the repeated text studies

The reported text runs used Ollama 0.33.0 and `qwen3:14b` with digest:

```text
bdbd181c33f2ed1b31c972991882db3cf4d192569092138a7d29e973cd9debe8
```

Prepare the datasets first, check that exact digest with `ollama show
qwen3:14b`, and configure the frozen runtime:

```bash
export OLLAMA_FLASH_ATTENTION=1 OLLAMA_KV_CACHE_TYPE=q8_0
export OLLAMA_NUM_PARALLEL=2 OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_KEEP_ALIVE=-1
```

Run the three-seed replications into a new ignored output directory:

```bash
reproduce/.venv/bin/python experiments/variance-study/run_variance_study.py \
  --dataset-root tmp/confirmatory-datasets \
  --output-root tmp/reproduction-runs/variance
```

Run the fresh quality-first study:

```bash
reproduce/.venv/bin/python experiments/quality-first-replications/run_study.py \
  --dataset-root tmp/quality-first-datasets \
  --output-root tmp/reproduction-runs/quality-first
```

Commands for the original text comparisons and the document baselines are in
the README or dataset protocol inside each experiment directory. Always compare
dataset hashes, model digest, SOP hashes, prompts, runtime settings, and split
before comparing a new run with the committed result.
