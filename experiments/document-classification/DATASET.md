# Document classification dataset and subset protocol

## Source data

The dry run uses **QS-OCR-Small v1.0**, the OCR-text version of the
Tobacco3482 document-classification dataset.

- Dataset page: https://github.com/QuickSign/ocrized-text-dataset
- Direct release artifact: https://github.com/QuickSign/ocrized-text-dataset/releases/download/v1.0/QS-OCR-small.tar.gz
- Downloaded artifact SHA-256: `9fb802036a2d95159a2fcb7c7bcd35ccbcc6d590f1cf39e7229a4fa9ee608b76`
- Upstream size: 3,482 OCR text documents in 10 classes

The original labels are checked against the annotations published with the
Tobacco3482 label-quality audit:

- Audit repository: https://github.com/gordon-lim/tobacco3482-mistakes
- Audit paper: https://arxiv.org/abs/2412.13140
- Annotation file: `tobacco3482_multi_labels.csv`
- Downloaded annotation SHA-256: `1bbe87ee7e8e1c2c54e67ca95c84025c13e09990089fa9c3e9a10059b66fb5e4`

Raw source documents stay outside version control until their content has been
reviewed for sensitive information. The repository stores only provenance,
selection metadata, derived eval rows approved for the experiment, and code
needed to reproduce the selection.

## Confirmatory paper subset

QS-OCR-Small and Tobacco3482 are one underlying dataset, not two independent
benchmarks. The confirmatory selector excludes every earlier pilot ID and uses
100 balanced development cases, 100 balanced validation cases, and 1,000
proportionally allocated untouched test cases. The test cannot be balanced at
100 per class because the corrected `scientific` class has only 88 eligible
items after pilot exclusion. Runtime paths contain IDs only; label-named paths
are forbidden because they expose the answer.

```bash
python experiments/document-classification/scripts/select_subset.py \
  --corpus tmp/qs-ocr-small \
  --audit tmp/tobacco3482-mistakes/tobacco3482_multi_labels.csv \
  --exclude-selection tmp/document-classification-subset/selection.json \
  --output tmp/paper-datasets/qs-ocr-confirmatory
python datasets/scripts/audit_document_subset.py \
  --dataset tmp/paper-datasets/qs-ocr-confirmatory \
  --output experiments/document-classification/confirmatory-dataset-proof.json
```

The committed proof passes all recorded separation, source-hash, leakage,
pilot-overlap, duplicate-content, and byte-repeat checks. The confirmatory NL
baseline completed on all 100 validation documents at 70% accuracy (macro F1
0.703), below the prespecified local 80% viability floor. The hybrid validation run
was therefore skipped and all 1,000 test documents remain untouched.

## Purpose of the first subset

The first run is a pipeline and evolution dry run, not a statistically strong
benchmark. It uses 20 documents: two examples from each of the 10 classes.

| Split | Cases per class | Total | Purpose |
| --- | ---: | ---: | --- |
| development | 1 | 10 | inspect traces and propose an SOP change |
| validation | 1 | 10 | accept or reject the proposed change |

There is no held-out split in this historical plumbing test. Its IDs are
excluded from the confirmatory dataset.

## Deterministic selection procedure

Use selection seed `20260902` and apply the following procedure without looking
at model predictions:

1. Match each OCR filename to the audit filename by its normalized numeric stem.
2. Exclude an OCR document when it is empty, has no matching audit record, or
   the audit assigns zero or more than one valid label.
3. Use the audit's single corrected label as the expected output. Normalize
   `ADVE` to `advertisement`; lowercase all other canonical labels.
4. Group eligible documents by corrected label and sort each group by stable
   normalized identifier before applying the seeded shuffle.
5. Take the first two eligible documents from each shuffled class group.
6. Assign the first selected document in each class to `development` and the
   second to `validation`.

This produces a class-balanced subset while preventing model performance,
document readability, or preferred examples from influencing selection.

## Review and replacement policy

After deterministic selection, inspect the 20 documents only for unusable or
sensitive content. Do not replace a document merely because it looks difficult.
Allowed rejection reasons are:

- empty or effectively empty OCR missed by the mechanical check;
- corrupt or unreadable content;
- sensitive personal information unsuitable for the experiment;
- an identifier or audit-mapping error.

Record every rejection and reason. Choose a replacement by taking the next
document from the same class's already-seeded order. Never choose a replacement
based on an agent prediction.

## Eval representation

The frozen `evals.csv` uses these required columns:

```csv
input,output,reasoning
data/documents/email/example.txt,email,"Contains email-specific structural evidence such as sender, recipient, or subject fields."
```

The experiment may additionally store `id` and `split`. `reasoning` is a short
annotator justification based on observable document evidence; it is not model
chain-of-thought. At runtime, the agent receives only `input`. Expected output,
reasoning, split, and audit annotations remain hidden.

## Required provenance artifacts

When the subset is generated, retain:

- `selection.json`: seed, input hashes, ordered candidates, selected IDs,
  exclusions, review rejections, replacements, and final split;
- `evals.csv`: frozen evaluation cases;
- `dataset-summary.json`: counts before and after every filter, by class;
- the selection script and its tests;
- the Ollama model name and digest used for each run.

These artifacts are required before reporting accuracy from the subset.
