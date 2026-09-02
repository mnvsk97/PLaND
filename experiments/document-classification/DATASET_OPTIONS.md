# Dataset options for the next experiment

Dataset candidates supplied by co-author Asit Sahoo were reviewed after the
schema-v2 measurement and invariant machinery was completed.

## RVL-CDIP: recommended primary benchmark

The official dataset contains 400,000 grayscale document images in 16 balanced
classes, with the standard 320,000 training, 40,000 validation, and 40,000 test
split. The full archive is approximately 37 GB. It is the stronger primary
benchmark because it adds six classes and substantially greater source
diversity.

Do not run an LLM agent over all 400,000 documents. For the next PLaND study,
use a deterministic stratified subset selected from the official splits before
model execution. Retain the original test split as a true held-out source and
record identifiers, seed, class counts, source checksums, exclusions, and OCR
procedure. Download labels first; acquire only the selected images when the
distribution mechanism permits it.

Important caveats:

- the images require OCR or a vision-capable local model;
- the source is historical tobacco-industry material and may contain sensitive
  information;
- published audits report label ambiguity, category-definition problems, and
  overlap concerns, so claims should use an audited subset or include label-noise
  sensitivity analysis;
- license and redistribution terms must be confirmed before committing any
  image or OCR content.

Official page: https://adamharley.com/rvl-cdip/

## Tobacco-3482: useful secondary benchmark, not independent here

Tobacco-3482 contains 3,482 document images in 10 classes. The supplied Kaggle
mirror is usable for local research subject to its source copyright terms:
https://www.kaggle.com/datasets/patrickaudriaz/tobacco3482jpg

However, the current proof-of-concept already uses QS-OCR-Small, which is OCR
derived from Tobacco-3482. Re-running the Kaggle JPG mirror would therefore be
an image/OCR-modality replication, not an independent secondary benchmark. It
is still useful for measuring whether deterministic OCR preprocessing changes
the NL-versus-hybrid result and for reconciling the audited label corrections.

Recent label-audit work reports substantial ambiguity and label errors. Continue
using corrected single-label records and document every exclusion rather than
assuming the folder label is ground truth.

## Recommendation

1. Use a frozen, stratified RVL-CDIP subset as the next primary experiment.
2. Use Tobacco-3482 JPG only for a raw-image/OCR ablation against the existing
   QS-OCR-Small result.
3. Keep both datasets outside Git; commit only selection code, identifiers,
   checksums, aggregate metadata, and safe comparison artifacts.
4. Add a true held-out split and repeated seeds before making general claims.
