# PLaND datasets

This directory prepares frozen, reviewable evaluation subsets for PLaND. The
preparation code uses only the Python standard library and public download
endpoints. It does not call paid APIs.

## Benchmark categories used in the paper

For the paper, we test PLaND across three categories rather than drawing a
conclusion from one kind of task:

| Category | Datasets | What it tests |
| --- | --- | --- |
| Text classification | LEDGAR, CFPB complaints, and SpamAssassin email | Whether deterministic steps can reduce repeated language-model work while preserving semantic classification quality. |
| Multi-step workflow | tau-retail | Whether a hybrid SOP can preserve policy compliance and correct tool-driven state changes. |
| Multimodal workflow | SROIE, with the existing Tobacco/RVL subset as robustness validation | Whether the method still works when document images, OCR, extraction, and validation add another source of error. |

These categories are the experimental scope selected for this paper. They are
not intended to cover every possible agent workflow. Together they provide a
text-only task, a policy-and-tools task, and a document-image task, allowing us
to test whether the result generalizes across different sources of
nondeterminism.

## Canonical case format

Every `evals.csv` contains these columns:

| Column | Meaning |
| --- | --- |
| `schema_version` | Currently `2`. |
| `id` | Stable case identifier within the benchmark. |
| `benchmark` | Dataset and task name. |
| `task_type` | `text_classification`, `tool_workflow`, or `multimodal_extraction`. |
| `split` | `development`, `validation`, or `test`. |
| `input` | Relative path to a UTF-8 JSON case file. |
| `output` | Compact JSON containing only the expected answer. |
| `reasoning` | Short annotation/evaluation rationale, never hidden chain-of-thought. |
| `metadata` | Compact JSON with source identifiers and task-specific fields. |

The JSON file referenced by `input` is the complete runtime input. Labels,
expected state, scorer data, and `reasoning` must not be exposed to the agent.
This path-based representation keeps CSV quoting manageable and supports text,
images, policies, and tool-workflow state through the same envelope.

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

python datasets/scripts/prepare_data.py tau-retail \
  --output tmp/enterprise-data/tau-retail

python datasets/scripts/prepare_data.py sroie \
  --output tmp/enterprise-data/sroie

python datasets/scripts/prepare_data.py spamassassin \
  --output tmp/enterprise-data/spamassassin
```

Use `--source` to prepare an already downloaded source without network access.
The selector ranks cases by `SHA-256(seed, source id)`, so input ordering cannot
change the subset. Output directories must not already exist.

The default split is 60 development, 20 validation, and 20 test cases. LEDGAR
and CFPB additionally use `--classes 10` and select a balanced subset. A class
must have enough eligible examples for every split or preparation fails.

CFPB preparation freezes a bounded response containing the latest 10,000
public complaints with narratives from the official CFPB search API, then
selects the balanced subset from that snapshot. This avoids downloading the
roughly 1.4 GB mutable bulk export. Keep the API response in ignored local
storage and retain its SHA-256 digest in `selection.json`.

The paper's resource-bounded text experiments derive a second, predeclared
20-case subset from each frozen 100-case snapshot: the two lowest seeded hashes
per label, assigned to 12 development, four validation, and four test cases.
The selector is `experiments/text-classification/scripts/select_paper_subset.py`.

SROIE saves both the source image and the dataset-provided OCR words. This
supports two experiments with identical cases: frozen OCR and raw-image
end-to-end processing.

SROIE row indexes restart independently in the upstream train and test splits.
Prepared IDs therefore include the upstream split (for example,
`receipt-train-12` and `receipt-test-12`) so cases and images cannot overwrite
one another.

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
| tau-retail | Policy-constrained tool workflow | task success and final database state | tokens, latency, tool calls, estimated cost |
| SROIE frozen OCR | Receipt field extraction with fixed OCR input | field F1 and exact match | tokens, agent latency, estimated cost |
| SROIE end to end | Image-to-structured receipt processing | field F1 and exact match | OCR quality, OCR latency, agent latency, total latency |

For every dataset:

1. Prepare one frozen dataset directory and retain `selection.json`.
2. Review cases only for corruption, unusable content, or sensitive data. Record
   every exclusion and use the next case in the precomputed seeded order.
3. Freeze the model and digest, system prompt, harness, evaluation cases,
   expected outputs, scorer, datasource hashes, seed, and permissions.
4. Measure the natural-language SOP baseline on the development, validation,
   and test splits.
5. Evolve only the SOP skill package using development feedback. Use validation
   to accept or reject candidates; do not inspect test results while evolving.
6. Run the accepted hybrid SOP once on the test split.
7. Compare NL and hybrid runs using the same cases and report accuracy or task
   success, tokens, latency, cost, resource usage, and SOP representation.

The comparison is valid only when the frozen invariant hashes match. Accuracy
is a quality floor: a candidate is useful only when it preserves the configured
quality requirement and improves the selected expense objective.

### Text classification

The runtime input is a case JSON file containing only the text. `output` holds
the hidden label. Use stratified metrics because the full upstream datasets are
not naturally balanced, even though the default prepared subset is balanced.

### Tool workflow

The tau-retail case exposes the policy, user scenario, and initial state. Its
evaluation criteria remain in `output` and must never be included in the agent
prompt. The tau environment and simulated tools are required to execute and
score these cases; this preparation script only freezes task selection and
inputs.

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
