# LEDGAR accuracy-recovery experiment

This is a new, prospective experiment. It does not alter or reinterpret the
committed three-run variance evidence. The protocol prioritizes quality before
expense and prohibits candidate mining after the fresh test holdout is opened.

The pinned LEDGAR snapshot cannot support another balanced 1,000-case test set
after excluding the prior confirmatory selection. The largest fresh balanced
holdout is 750 cases: 75 unused official-test cases for each of the same ten
labels. The protocol also requests 500 development and 500 validation cases.

Run the non-mutating preflight before preparing any new selection:

```bash
python3 experiments/ledgar-accuracy-recovery/preflight.py \
  --source-dir /path/to/pinned/ledgar/sources
```

The preflight validates source hashes, unused balanced capacity, the frozen
model identity, strict comparison-gate support, and Git cleanliness. It does
not select cases, inspect a new holdout, or invoke the model.

Once the preflight passes, reconstruct the prior confirmatory dataset from the
pinned sources and seed, then prepare the new dataset with that complete prior
dataset supplied through `--exclude-dataset`. This preserves ID and normalized-
content exclusion across all prior splits. Lock one finalist on development and
validation before running the fresh test split.

The strict comparison command adds these gates to the existing paired scorer:

```bash
python3 experiments/text-classification/scripts/compare.py \
  --nl baseline-validation.json \
  --hybrid candidate-validation.json \
  --output comparison.json \
  --bootstrap-samples 5000 \
  --noninferiority-margin 0.005 \
  --minimum-token-reduction 0.20 \
  --minimum-accuracy 0.80 \
  --require-no-accuracy-regression \
  --minimum-accuracy-difference-lower-bound -0.005 \
  --max-per-label-recall-drop 0.02 \
  --minimum-command-precision 0.99
```
