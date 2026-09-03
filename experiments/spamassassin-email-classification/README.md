# SpamAssassin email-classification experiment

Classifies RFC-822 messages as `spam` or `ham`. Preparation removes headers
that reveal labels, deduplicates sanitized content, and freezes balanced splits
of 100 development, 100 validation, and 1,000 test emails. Pilot IDs/content are
excluded; see `confirmatory-dataset.json` and
`datasets/proofs/spamassassin-confirmatory.json`.

The evaluation contract is frozen; only the SOP and classifier may change from
development evidence. Because the corpus is from 2002-2003, results test the
PLaND mechanism, not current production phishing performance.

## Results

Validation rejected the candidate: accuracy fell from 90% to 86% with a paired
interval of [-9, +1] points, while tokens fell 4.08% with interval [1.02%,
8.50%]. It failed quality and minimum token-reduction gates, so test remained
untouched.

The optimized replication reached 88% versus 84% accuracy and 5.04% token
reduction. The token gate passed narrowly, but quality did not; test remains
unreleased. See `results/confirmatory-validation-*.json` and
`results/replication-20260902-validation-comparison.json`.

The earlier four-case held-out pilot fell from 100% to 75% accuracy. It is
retained in `RESULTS.md` as exploratory evidence, not generalization.
