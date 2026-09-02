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

## Frozen subset

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
