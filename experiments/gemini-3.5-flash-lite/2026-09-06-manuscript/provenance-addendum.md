# Manuscript evidence provenance addendum

This review uses collection commit `4ad24c9838922b3db777ac4ba4dbc34de7a449ae`.
No original collection output, plan, decision, ledger, or evidence manifest was
edited during manuscript integration. The paper-audit controller is a copy of
the packaged final SpamAssassin controller's state and ledger, continued in a
new directory. Its inherited entries still point to the original collection;
new commands are restricted to the paper-audit stage. It does not rerun models
or reopen any dataset gate.

## Scope of the current verification

The portable `evidence-files.json` inventories saved collection files and frozen
code, including interrupted and superseded attempts. The statistical audit
recomputes all reached paired repeats: development for all three datasets,
selection for all three, and final test only for LEDGAR and SpamAssassin. It
checks complete case counts, literal-label correctness, tokens, settings,
paired identities, development assessments, and all held-out bootstrap
intervals and decisions. It does not read CFPB final-test case inputs.

The original collection manifests use absolute paths and include directory
snapshots taken at different times. Their entry counts must not be described
as counts of individually verified immutable files. At manuscript review, all
file entries of the active LEDGAR, CFPB, and amendment-02 SpamAssassin manifests
matched their recorded hashes. Raw external inputs and historical directory
snapshots are not covered by the portable offline file inventory. Their
recorded source hashes and preparation audits remain in the original evidence.

## Corrections to metadata and the earlier collection summary

- The final SpamAssassin selection gate summary says `candidate-02`, inherited
  from a reused summarizer. The evaluated package is `candidate-01`, established
  by its SOP/classifier hashes and the run outputs. No candidate was added after
  selection and no numerical decision changes.
- Amendment-02 dataset metadata retains an amendment-number field of `1` from
  the generic builder. The authoritative frozen plan is amendment 02; its
  replacement lineage and final split hashes are recorded separately.
- The provider adapter records `seed_supported: false`. Repeat identifiers are
  not inference seeds sent to the service. Data and bootstrap seeds do operate.
- Final-test LEDGAR command coverage is 370/500, or 74.0%. The earlier collection
  report's 69.8% figure refers to selection, not final test. The manuscript uses
  case-level final-test coverage.
- One SpamAssassin selection email has different reported prompt-token counts
  between paired calls (differences of 1, 3, and 2 tokens). The input and baseline
  SOP construction remain fixed; receipts do not explain the discrepancy. It
  remains in token totals, is disclosed in the manuscript, and is not taken as
  proof that a prompt was shortened.
- The original SpamAssassin manifest points to five partial/failed files at
  their old paths. Their exact bytes are preserved under `interrupted-runs/`;
  the portable inventory covers their current locations. The first amendment's
  manifest has an older state-file hash than its packaged terminal state. That
  superseded manifest is retained as a historical record, not asserted to be a
  current full-directory verification. Its final state and failed outcomes are
  separately covered by the new portable inventory.

These clarifications supersede inconsistent prose in
`2026-09-05-11-41-pm/fresh-evaluation-report.md`, which is retained unchanged.
They do not alter any frozen raw output, accuracy, token count, gate, or final
test access decision. `paper-calculations.json` and the final manuscript are the
reviewed numerical report.

## Distribution boundary

The collection commit was not publicly retrievable during the initial
manuscript review. The author subsequently requested publication to `main`.
On September 6, 2026, collection commit
`4ad24c9838922b3db777ac4ba4dbc34de7a449ae` was pushed to the
[public repository](https://github.com/mnvsk97/PLaND). An unauthenticated
download of its frozen plan matched the local SHA-256 hash; the paper-audit
controller records this release check. The manuscript's availability statement
and links were then updated for publication. Raw licensed or private input
snapshots remain outside Git. No journal submission was performed.
