# CFPB complaint-routing experiment

Routes public complaint narratives into ten product queues. Preparation freezes
the official API response, balances 100 development, 100 validation, and 1,000
test cases, and excludes pilot IDs/content. See `confirmatory-dataset.json` and
`datasets/proofs/cfpb-confirmatory.json`.

The evaluation contract is frozen across variants; only the SOP and classifier
may change from development evidence. Complaint text and case traces remain in
ignored `tmp/`.

## Results

Validation rejected the candidate. Accuracy was 79% NL versus 72% hybrid; the
paired difference interval was [-13, -2] points, and NL missed the 80% viability
floor. A 41.75% token reduction therefore did not release the 1,000-case test.

The optimized replication reached 78% versus 71% accuracy and reduced tokens
43.26%, again failing quality and viability. The test remains untouched.

See `results/confirmatory-validation-*.json` and
`results/replication-20260902-validation-comparison.json`. The earlier
20-case result is exploratory and does not override this rejection.
