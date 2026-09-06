# PLaND datasets

This directory prepares frozen evaluation subsets with standard-library Python
and public downloads. Repository setup instructions are in
[`../README.md`](../README.md).

## Scope and format

| Datasets | Purpose |
| --- | --- |
| LEDGAR, CFPB, SpamAssassin | Test whether stable rules can bypass model work while preserving semantic quality. |

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

Without the frozen CFPB snapshot, a current download is a new dataset condition,
not an exact reproduction. Selection ranks cases by
`SHA-256(seed, source id)`, deduplicates normalized content, and excludes pilot
IDs and content. Output directories must not exist. LEDGAR preserves official
LexGLUE splits; CFPB and SpamAssassin use seeded disjoint splits because they
lack equivalent boundaries. CFPB freezes the API response and records its hash.

## Locked sources

[`sources.lock.json`](sources.lock.json) records the exact source revisions,
file sizes, SHA-256 values, upstream-terms links, and redistribution boundary.
It covers the three paper datasets. Raw records remain outside Git under
`tmp/`. A hash mismatch is a different dataset condition and must not be
presented as an exact reproduction.

## Current collection

The reviewed `plan.json` and `protocol.md` are stored inside the timestamped
model run. The collection uses 500 development, 1,000 selection, and 500
final-test cases per dataset. The preparer verifies locked raw bytes, excludes
previously opened splits and normalized-content duplicates, preserves unopened
held-out splits, and writes a new freeze manifest atomically:

```bash
python datasets/scripts/prepare_collection.py \
  --plan experiments/<model-name>/<date-time>/plan.json \
  --output tmp/<model-name>/<date-time>/datasets/ledgar
```

Invoke preparation through the collection controller. Run LEDGAR first, then
CFPB and SpamAssassin, retaining each freshness receipt and every failed attempt.

## Confirmatory populations

| Dataset | Development / validation / test | Audit | Experiment |
| --- | ---: | --- | --- |
| LEDGAR | 100 / 100 / 1,000 | Passed; identical repeat | Validation passed; test plus three optimized replications |
| CFPB | 100 / 100 / 1,000 | Passed; identical repeat | Validation rejection repeated three times; test untouched |
| SpamAssassin | 100 / 100 / 1,000 | Passed; identical repeat | Validation rejection repeated three times; test untouched |

## Evaluation rules

1. Freeze the dataset, model/digest, prompt, harness, scorer, seed, permissions,
   expected outputs, and datasource hashes.
2. Measure the natural-language SOP; evolve only the skill package using
   development evidence.
3. Let validation accept or reject candidates. Release test only after the
   paired validation gate passes.
4. Compare matching cases and report the task-specific quality metric plus
   tokens, calls, latency, cost, resources, and representation.

Use accuracy and macro F1 for the three classification datasets.

Every new run records the `evals.csv` and `selection.json` SHA-256 values. Raw
source records remain in ignored `tmp/` and are not present in committed result
JSON.

Run dataset tests with:

```bash
python -m unittest discover -s datasets/tests -v
```
