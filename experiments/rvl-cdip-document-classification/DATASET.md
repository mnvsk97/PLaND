# RVL-CDIP subset protocol

## Source

RVL-CDIP contains 400,000 grayscale document images in 16 balanced classes,
with an official 320,000/40,000/40,000 train/validation/test split. The full
archive is about 37 GB.

- Canonical dataset page: https://adamharley.com/rvl-cdip/
- Sampling mirror: https://huggingface.co/datasets/jordyvl/rvl_cdip_100_examples_per_class
- Mirror scope: 100 examples per class, retaining train/validation/test splits

The experiment uses the smaller mirror only to avoid downloading the full
archive. This is an RVL-CDIP subset experiment, not a full-benchmark result.

## Confirmatory subset and mirror capacity

Development comes only from official train, validation only from official
validation, and test only from official test. After excluding all 32 pilot IDs,
the mirror has 384 untouched test images before OCR validation. Fifteen produce
empty local Tesseract output and are excluded, leaving 100 development, 100
validation, and 369 usable test cases. The requested 1,000 test target therefore
has a recorded 631-case shortfall; no image is moved across official splits.
Runtime paths contain no class label.

```bash
python experiments/rvl-cdip-document-classification/scripts/select_subset.py \
  --exclude-selection tmp/rvl-cdip-subset/selection.json \
  --output tmp/paper-datasets/rvl-cdip-confirmatory
python datasets/scripts/audit_document_subset.py \
  --dataset tmp/paper-datasets/rvl-cdip-confirmatory \
  --pilot-dataset tmp/rvl-cdip-subset \
  --output experiments/rvl-cdip-document-classification/confirmatory-dataset-proof.json
```

The full official archive is about 37 GB and would remove this mirror ceiling,
but it is outside this preparation run.

The committed proof passes the recorded separation, source-hash, leakage,
pilot-overlap, and official-split checks. Exact repeat preparation is not
recorded for this network-backed mirror, so reproducibility is supported by the
frozen revision and hashes rather than a second byte-for-byte download. The
confirmatory natural-language validation baseline reached 50% accuracy and
0.4724 macro F1 on 100 cases. This was below the prespecified 80% viability
floor, so the hybrid condition was not run and all 369 test cases remained
untouched. The historical 32-case result below remains a pilot.

## Historical frozen subset

Select 32 documents: one validation image and one test image from each of the
16 classes. Official validation images form the PLaND development split; official
test images form the PLaND validation split. Seed `20260902` selects one row
within each class without examining image content or model predictions.

Run local Tesseract OCR once during dataset preparation. The resulting OCR text,
not the image or expected label, is supplied to both agents. OCR output and its
hash are frozen before baseline measurement, so OCR time and variability are
outside both measured variants.

The selection artifact records repository revision, source split and row,
image URL, image hash, OCR hash, Tesseract version, seed, and class. Raw images
and OCR text remain under ignored `tmp/`; committed results contain provenance
and aggregate measurements only.
