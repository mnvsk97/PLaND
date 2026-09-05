# PLaND datasets

This directory prepares frozen evaluation subsets with standard-library Python
and public downloads. Repository setup and Ollama instructions are in
[`../README.md`](../README.md).

## Scope and format

| Category | Datasets | Purpose |
| --- | --- | --- |
| Text classification | LEDGAR, CFPB, SpamAssassin | Test whether stable rules can bypass model work while preserving semantic quality. |
| Document image | SROIE, Tobacco/RVL | Add OCR, extraction, and perceptual error. |

Each `evals.csv` uses schema version 2 and contains `id`, `benchmark`,
`task_type`, `split`, `input`, `output`, `reasoning`, and `metadata`. `input`
points to the complete runtime JSON; hidden labels, expected state, scorer data,
and reasoning must never be exposed to the agent.

A prepared directory also contains `selection.json` (source, seed, rules,
hashes, and selected records), `dataset-summary.json`, and immutable inputs in
`data/`.

## Prepare and audit

Create the earlier pilot selections before the confirmatory selections because
the latter exclude every pilot ID and normalized content. LEDGAR and
SpamAssassin can be fetched by the preparer. The confirmatory design uses 100
development, 100 validation, and 1,000 test cases:

```bash
for dataset in ledgar spamassassin; do
  python datasets/scripts/prepare_data.py "$dataset" \
    --output "tmp/paper-datasets/$dataset"
  python datasets/scripts/prepare_data.py "$dataset" \
    --output "tmp/confirmatory-datasets/$dataset" \
    --exclude-dataset "tmp/paper-datasets/$dataset" \
    --development-cases 100 --validation-cases 100 --test-cases 1000
done
```

CFPB's upstream API is live and mutable. Exact reconstruction therefore
requires the local snapshot whose hash appears in `sources.lock.json`:

```bash
python datasets/scripts/prepare_data.py cfpb \
  --source tmp/source-snapshots/cfpb/complaints-api.json \
  --output tmp/paper-datasets/cfpb
python datasets/scripts/prepare_data.py cfpb \
  --source tmp/source-snapshots/cfpb/complaints-api.json \
  --output tmp/confirmatory-datasets/cfpb \
  --exclude-dataset tmp/paper-datasets/cfpb \
  --development-cases 100 --validation-cases 100 --test-cases 1000
```

SROIE exact reconstruction similarly requires the frozen rows snapshot:

```bash
python datasets/scripts/prepare_data.py sroie \
  --source tmp/source-snapshots/sroie/rows.json \
  --output tmp/datasets/sroie

python datasets/scripts/prepare_data.py sroie \
  --source tmp/source-snapshots/sroie/rows.json \
  --exclude-selection tmp/datasets/sroie/selection.json \
  --development-cases 100 --validation-cases 100 --test-cases 347 \
  --output tmp/paper-datasets/sroie-confirmatory
```

Without either frozen snapshot, a current download is a new dataset condition,
not an exact reproduction. Selection ranks cases by
`SHA-256(seed, source id)`, deduplicates normalized content, and excludes pilot
IDs and content. Output directories must not exist. LEDGAR preserves official
LexGLUE splits; CFPB and SpamAssassin use seeded disjoint splits because they
lack equivalent boundaries. CFPB freezes the API response and records its hash.

Audit and create check-in-safe proof metadata without raw text:

```bash
python datasets/scripts/audit_prepared.py \
  --dataset tmp/confirmatory-datasets/ledgar \
  --repeat-dataset tmp/confirmatory-repeat/ledgar \
  --output datasets/proofs/ledgar-confirmatory.json
```

Proofs cover counts, balance, source and case hashes, missing files, duplicate
IDs/content, label leakage, pilot overlap, exclusions, split integrity, and
repeat preparation.

## Locked sources and quality-first reconstruction

[`sources.lock.json`](sources.lock.json) records the exact source revisions,
file sizes, SHA-256 values, upstream-terms links, and redistribution boundary.
It covers every paper dataset, including QS-OCR/Tobacco3482, SROIE, and the
RVL-CDIP sampling mirror. Raw records remain outside Git under `tmp/`. A hash mismatch is a different
dataset condition and must not be presented as an exact reproduction.

The later quality-first validation datasets are rebuilt with one command. It
verifies the frozen raw bytes, verifies each original 1,200-case confirmatory
selection, freezes the same labels, excludes prior IDs and normalized content,
and checks the resulting `evals.csv` and `selection.json` hashes:

```bash
python datasets/scripts/prepare_quality_first.py \
  --source-root tmp/source-snapshots \
  --confirmatory-root tmp/confirmatory-datasets \
  --output tmp/quality-first-datasets
```

The source root must contain the paths listed in `sources.lock.json`. LEDGAR
and SpamAssassin files can be downloaded from their locked URLs. The CFPB API
is mutable, so exact reproduction requires the frozen `complaints-api.json`
snapshot with the recorded hash; a fresh API response is intentionally
rejected. Use `--check-inputs-only` to validate source custody and the prior
selection without creating outputs. The command creates all three datasets in
a staging directory and publishes the output only after every expected hash
matches.

## Confirmatory populations

| Dataset | Development / validation / test | Audit | Experiment |
| --- | ---: | --- | --- |
| LEDGAR | 100 / 100 / 1,000 | Passed; identical repeat | Validation passed; test plus three optimized replications |
| CFPB | 100 / 100 / 1,000 | Passed; identical repeat | Validation rejection repeated three times; test untouched |
| SpamAssassin | 100 / 100 / 1,000 | Passed; identical repeat | Validation rejection repeated three times; test untouched |
| QS-OCR/Tobacco3482 | 100 / 100 / 1,000 | Passed; identical repeat | Baseline nonviable |
| SROIE | 100 / 100 / 300 | Passed after duplicate exclusions | Baseline nonviable |
| RVL-CDIP mirror | 100 / 100 / 369 | Passed; repeat not recorded | Baseline nonviable |

SROIE uses all eligible official-test receipts after exclusions; RVL has a
631-case test-capacity shortfall. Neither is padded across source boundaries.
SROIE IDs include the upstream split because row indexes restart in train and
test. The same SROIE cases support frozen-OCR and raw-image runs.

## Evaluation rules

1. Freeze the dataset, model/digest, prompt, harness, scorer, seed, permissions,
   expected outputs, and datasource hashes.
2. Measure the natural-language SOP; evolve only the skill package using
   development evidence.
3. Let validation accept or reject candidates. Release test only after the
   paired validation gate passes.
4. Compare matching cases and report the task-specific quality metric plus
   tokens, calls, latency, cost, resources, and representation.

Use accuracy/macro F1 for classification and field F1/exact match for SROIE.
Never combine those metrics into one score. Frozen-OCR and end-to-end SROIE
runs are separate conditions; OCR engine, version, configuration, and output
hash are invariants.

The three-seed text variance study reuses these exact prepared snapshots; its
cross-run summary is `experiments/variance-study/summary.json`, and every run
records the `evals.csv` and `selection.json` SHA-256 values. Raw source records
remain in ignored `tmp/` and are not present in committed result JSON.

Run dataset tests with:

```bash
python -m unittest discover -s datasets/tests -v
```
