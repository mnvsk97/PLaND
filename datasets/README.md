# PLaND datasets

Repository-level setup, optimized Ollama instructions, paired run commands, and
paper artifacts are documented in [`../README.md`](../README.md).

This directory prepares frozen, reviewable evaluation subsets for PLaND. The
preparation code uses only the Python standard library and public download
endpoints. It does not call paid APIs.

## Benchmark categories used in the paper

For the paper, we test PLaND across two active categories rather than drawing a
conclusion from one kind of task:

| Category | Datasets | What it tests |
| --- | --- | --- |
| Text classification | LEDGAR, CFPB complaints, and SpamAssassin email | Whether deterministic steps can reduce repeated language-model work while preserving semantic classification quality. |
| Multimodal workflow | SROIE, with the existing Tobacco/RVL subset as robustness validation | Whether the method still works when document images, OCR, extraction, and validation add another source of error. |

These categories are the experimental scope selected for this paper. They are
not intended to cover every possible agent workflow. Together they provide
text-only and document-image tasks, allowing us to test whether the result
generalizes across semantic and perceptual sources of nondeterminism.

## Canonical case format

Every `evals.csv` contains these columns:

| Column | Meaning |
| --- | --- |
| `schema_version` | Currently `2`. |
| `id` | Stable case identifier within the benchmark. |
| `benchmark` | Dataset and task name. |
| `task_type` | `text_classification` or `multimodal_extraction`. |
| `split` | `development`, `validation`, or `test`. |
| `input` | Relative path to a UTF-8 JSON case file. |
| `output` | Compact JSON containing only the expected answer. |
| `reasoning` | Short annotation/evaluation rationale, never hidden chain-of-thought. |
| `metadata` | Compact JSON with source identifiers and task-specific fields. |

The JSON file referenced by `input` is the complete runtime input. Labels,
expected state, scorer data, and `reasoning` must not be exposed to the agent.
This path-based representation keeps CSV quoting manageable and supports text
and images through the same envelope.

Each prepared directory also contains:

- `selection.json`: source revision, seed, selection rule, hashes, and records;
- `dataset-summary.json`: counts by split and label;
- `data/`: immutable case inputs and downloaded media.

## Prepare a dataset

Prepare one dataset (100 cases by default):

```bash
python datasets/scripts/prepare_data.py ledgar \
  --output tmp/enterprise-data/ledgar

python datasets/scripts/prepare_data.py cfpb \
  --output tmp/enterprise-data/cfpb

python datasets/scripts/prepare_data.py sroie \
  --exclude-selection tmp/datasets/sroie/selection.json \
  --development-cases 100 --validation-cases 100 --test-cases 347 \
  --output tmp/paper-datasets/sroie-confirmatory

python datasets/scripts/prepare_data.py spamassassin \
  --output tmp/enterprise-data/spamassassin
```

Use `--source` to prepare an already downloaded source without network access.
The selector ranks cases by `SHA-256(seed, source id)`, so input ordering cannot
change the subset. Output directories must not already exist.

The legacy/default 100-case preparation uses a 60/20/20 split. The confirmatory
text design uses 100 development, 100 validation, and 1,000 untouched test
cases for each active text dataset:

```bash
for dataset in ledgar cfpb spamassassin; do
  python datasets/scripts/prepare_data.py "$dataset" \
    --output "tmp/confirmatory-datasets/$dataset" \
    --exclude-dataset "tmp/paper-datasets/$dataset" \
    --development-cases 100 --validation-cases 100 --test-cases 1000
done
```

LEDGAR and CFPB use ten classes (10/10/100 cases per class); SpamAssassin uses
two classes (50/50/500 per class). Exact normalized content is deduplicated
before selection. Selection is global, deterministic, and disjoint, so the
test set remains untouched until SOP candidate selection is complete.
The exclusion is matched on both source ID and normalized content, preventing a
pilot case from reappearing under another ID. Its eval hash and case-manifest
hash are saved in the new selection manifest.

LEDGAR additionally preserves the official LexGLUE boundaries: confirmatory
development comes only from upstream `train`, validation only from upstream
`validation`, and test only from upstream `test`. CFPB and SpamAssassin do not
provide equivalent official benchmark splits, so their splits use the seeded,
disjoint selection described above.

CFPB preparation freezes 1,000 public narrative complaints for each of ten
predeclared current product labels from the official CFPB search API, then
deduplicates and selects from that snapshot. This avoids downloading the
roughly 1.4 GB mutable bulk export and prevents recent high-volume products
from crowding out lower-volume labels. Keep the API response in ignored local
storage and retain its SHA-256 digest in `selection.json`.

The paper's resource-bounded text experiments derive a second, predeclared
20-case subset from each frozen 100-case snapshot: the two lowest seeded hashes
per label, assigned to 12 development, four validation, and four test cases.
The selector is `experiments/text-classification/scripts/select_paper_subset.py`.
Those 20-case results are pilots and do not replace the confirmatory design.

Audit and publish check-in-safe proof metadata without committing raw text:

```bash
python datasets/scripts/audit_prepared.py \
  --dataset tmp/confirmatory-datasets/ledgar \
  --repeat-dataset tmp/confirmatory-repeat/ledgar \
  --output datasets/proofs/ledgar-confirmatory.json
```

The proof records counts, per-split balance, source/eval/selection/case hashes,
ID overlap, normalized-content duplicates, structural label leakage, missing
cases, pilot overlap, exclusion-manifest identity, upstream split integrity,
and byte-identical repeat preparation. Equivalent proof files are kept
for CFPB and SpamAssassin under `datasets/proofs/`.

## Prepared confirmatory datasets

The committed proof artifacts record the following frozen populations. A
passing data audit establishes provenance, separation, and reproducibility; it
does not mean that the NL-versus-hybrid model experiment has passed.

| Dataset | Development | Validation | Untouched test | Audit status | Experiment status |
| --- | ---: | ---: | ---: | --- | --- |
| LEDGAR | 100 | 100 | 1,000 | Passed; byte-identical repeat | Validation passed; one-time test completed |
| CFPB complaints | 100 | 100 | 1,000 | Passed; byte-identical repeat | Validation rejected; test remains untouched |
| SpamAssassin | 100 | 100 | 1,000 | Passed; byte-identical repeat | Validation rejected; test remains untouched |
| QS-OCR-Small / Tobacco3482 | 100 | 100 | 1,000 | Passed; byte-identical repeat | Baseline validation nonviable; test untouched |
| SROIE | 100 | 100 | 300 | Passed; byte-identical repeat after removing three cross-ID pilot-image duplicates | Baseline validation nonviable; test untouched |
| RVL-CDIP constrained mirror | 100 | 100 | 369 | Passed; repeat not recorded | Baseline validation nonviable; test untouched |

SROIE uses all eligible official-test receipts after prior-pilot and exact-image
exclusions. The RVL mirror cannot supply the requested 1,000-case test: its
proof records a 631-case capacity shortfall. No case is moved across an
official source split to fill either shortfall.

SROIE saves both the source image and the dataset-provided OCR words. This
supports two experiments with identical cases: frozen OCR and raw-image
end-to-end processing.

SROIE row indexes restart independently in the upstream train and test splits.
Prepared IDs therefore include the upstream split (for example,
`receipt-train-12` and `receipt-test-12`) so cases and images cannot overwrite
one another.

For the confirmatory preparation, development and validation are disjoint
selections from the official 626-receipt train split. Test contains every
unique official test receipt not used by the pilot. Exact image duplicates and
pilot IDs are recorded as exclusions rather than being moved between official
splits. Audit it with `datasets/scripts/audit_sroie.py`.

WorkArena is intentionally excluded: its code is public, but a prepared
ServiceNow instance requires gated access. The existing Tobacco/RVL scripts
remain under their original experiment directories.

## Use the prepared data in experiments

The datasets test different parts of the PLaND hypothesis. Do not merge their
scores into one accuracy number.

| Dataset | Experiment | Primary quality metric | Additional measurements |
| --- | --- | --- | --- |
| LEDGAR | Contract-clause classification | macro F1 and accuracy | tokens, latency, estimated cost, resources |
| CFPB | Complaint product routing | macro F1 and accuracy | tokens, latency, estimated cost, resources |
| SpamAssassin | Raw-email spam or ham classification | spam F1, macro F1, and accuracy | tokens, latency, model calls, estimated cost |
| SROIE frozen OCR | Receipt field extraction with fixed OCR input | field F1 and exact match | tokens, agent latency, estimated cost |
| SROIE end to end | Image-to-structured receipt processing | field F1 and exact match | OCR quality, OCR latency, agent latency, total latency |

For every dataset:

1. Prepare one frozen dataset directory and retain `selection.json`.
2. Review cases only for corruption, unusable content, or sensitive data. Record
   every exclusion and use the next case in the precomputed seeded order.
3. Freeze the model and digest, system prompt, harness, evaluation cases,
   expected outputs, scorer, datasource hashes, seed, and permissions.
4. Measure the natural-language SOP baseline on development and validation.
5. Evolve only the SOP skill package using development feedback. Use validation
   to accept or reject candidates; do not inspect test inputs, predictions, or
   expected outputs while evolving.
6. Release the test split only after the paired validation gate passes. Run the
   frozen natural-language and accepted hybrid SOPs once on the same test cases.
7. Compare the paired runs and report accuracy or task
   success, tokens, latency, cost, resource usage, and SOP representation.

The comparison is valid only when the frozen invariant hashes match. Accuracy
is a quality floor: a candidate is useful only when it preserves the configured
quality requirement and improves the selected expense objective.

### Text classification

The runtime input is a case JSON file containing only the text. `output` holds
the hidden label. Use stratified metrics because the full upstream datasets are
not naturally balanced, even though the default prepared subset is balanced.

### Multimodal extraction

Run SROIE in two modes using the same selected IDs:

- **Frozen OCR:** give the agent `frozen_ocr`; this isolates SOP changes.
- **End to end:** give the agent the image; this measures the deployable pipeline.

Never compare a frozen-OCR NL run with an end-to-end hybrid run. OCR mode,
engine, version, configuration, and output hash are experimental invariants.

## Tests

```bash
python -m unittest discover -s datasets/tests -v
```
