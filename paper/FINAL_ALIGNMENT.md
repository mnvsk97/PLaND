# Final manuscript alignment

This record covers `output/paper/PLAND_SUBMISSION_READY_FINAL.pdf`, the approved
nine-page submission manuscript.

The approved composition is reproducible from the committed frozen inputs
`paper/final_submission/reviewed-base.pdf` and
`paper/final_submission/replacement-page-2.pdf`. The command
`python paper/build_final_submission.py` validates both input hashes and
reassembles the nine pages. Repeated builds with the locked dependency version
are byte-identical; `--check` compares every rebuilt page's media box and
content stream with the committed final without modifying it. The builder also
pins `paper/FINAL_TABLES.md`; `paper/generate_tables.py --check` regenerates
that snapshot from the committed evidence, so evidence drift or an unreflected
table change fails verification.

## Editorial and visual scope

- The manuscript preserves the reviewed source PDF except for Figure 1 and its
  caption on page 2, left column.
- Figure 1 now shows representative numbered lines from the actual LEDGAR
  natural-language and hybrid SOPs, including `python classify.py` and the
  command-abstention fallback.
- The graph-based SOP remains an explicitly conditional mature target: stable
  nodes execute deterministically while a few semantic nodes retain model
  reasoning.
- At 120 DPI, pages 1 and 3-9 render pixel-identically to the reviewed source.
  Page 2 was inspected at full-page and print-size resolution for legibility,
  clipping, overlap, headers, footer, and page number.

## Claim-to-evidence reconciliation

The final manuscript was checked against these committed sources:

- Original confirmatory results:
  `experiments/ledgar-text-classification/results/confirmatory-validation-comparison.json`,
  `experiments/ledgar-text-classification/results/confirmatory-test-comparison.json`,
  `experiments/cfpb-text-classification/results/confirmatory-validation-comparison.json`,
  and
  `experiments/spamassassin-email-classification/results/confirmatory-validation-comparison.json`.
- Three-seed optimized replications:
  `experiments/variance-study/summary.json` and the three experiment-local
  `results/variance-study-20260903/` directories.
- Fresh quality-first validations:
  `experiments/quality-first-replications/summary.json` and the three
  experiment-local `results/quality-first-validation-20260903/` directories.
- Dataset counts and separation:
  `datasets/proofs/ledgar-confirmatory.json`,
  `datasets/proofs/cfpb-confirmatory.json`, and
  `datasets/proofs/spamassassin-confirmatory.json`.
- Earlier pilot boundaries: the experiment-local `RESULTS.md` files for
  document classification, RVL-CDIP, SpamAssassin, and SROIE.

Verified headline values include:

- Original LEDGAR test: 93.5% NL versus 92.7% hybrid; 376,088 versus 225,573
  tokens; 1,000 versus 589 model calls; 411 command-routed cases; paired
  difference interval [-1.6, 0.0] percentage points.
- Optimized LEDGAR replications: 93.7% versus 92.9%; mean 376,090 versus
  225,575.33 tokens; identical 411/589 command/model routing in three seeds.
- Quality-first validation: LEDGAR 93.6% versus 92.8%, CFPB 74.8% versus 73.8%,
  and SpamAssassin 90.2% versus 89.0%; all three candidates rejected and all
  corresponding test splits kept closed.
- Confirmatory dataset proofs: 1,200 cases per text dataset, divided into 100
  development, 100 validation, and 1,000 test cases, with unique identifiers
  and no split overlap, content duplicates, runtime label leakage, or pilot
  overlap.

The PDF's data-and-code statement points to `f9aa707`, the evidence commit on
which the final manuscript is based. This later editorial commit does not
change or rerun experimental results.

## Verification performed before check-in

- 94 unit tests across 21 test files passed using the repository virtual
  environment.
- Eight variance/quality-first checksum manifests covering 131 evidence files
  were checked. One stale central variance-study manifest was corrected for the
  already-committed `aggregate.py` and `tests/test_aggregate.py`; all
  experiment-local evidence manifests matched.
- The generated paper bundle was rebuilt successfully and its artifact hashes
  were refreshed in `output/paper/artifact-manifest.json`.
- The arXiv source bundle and its five-page local preview were regenerated with
  the same revised evolution-path figure; their hashes were refreshed in
  `output/arxiv/artifact-manifest.json`. No upload or submission was performed.
- `git diff --check` passed.

This is a repository-integrity and claim-reconciliation check, not a new model
run or a new statistical analysis.
