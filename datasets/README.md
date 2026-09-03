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

The confirmatory text design uses 100 development, 100 validation, and 1,000
test cases:

```bash
for dataset in ledgar cfpb spamassassin; do
  python datasets/scripts/prepare_data.py "$dataset" \
    --output "tmp/confirmatory-datasets/$dataset" \
    --exclude-dataset "tmp/paper-datasets/$dataset" \
    --development-cases 100 --validation-cases 100 --test-cases 1000
done

python datasets/scripts/prepare_data.py sroie \
  --exclude-selection tmp/datasets/sroie/selection.json \
  --development-cases 100 --validation-cases 100 --test-cases 347 \
  --output tmp/paper-datasets/sroie-confirmatory
```

Use `--source` for an existing local download. Selection ranks cases by
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
