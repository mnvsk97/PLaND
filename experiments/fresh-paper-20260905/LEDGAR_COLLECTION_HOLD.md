# LEDGAR collection: invalid freshness, stopped

The fresh run cannot be used as fresh paper evidence. The original exclusion
collector covered confirmatory and quality-first runs but missed the earliest
executed 20-case paper pilot, whose identities are in `paper-subset.json` and
whose measurements were retained as aggregate `results/summary.json`.

This was an operator implementation error, not a scientific rejection of the
method. Eighteen pilot IDs entered the new sample: 11 development, two selection,
and five reserved final-test cases. The original preparation audit's passing
result checked an incomplete exclusion list and is superseded by this incident.

## Actual stage reached

Baseline and one hybrid candidate completed development and selection. The
recorded statistical selection gate accepted before the final baseline started.
The operator stopped the pipeline after discovering the freshness failure; its
last saved final-baseline checkpoint contains 90 cases. Final hybrid and repeat
runs did not start. A checkpoint may omit in-flight requests, so the complete
500-case final reservation is quarantined rather than presumed unopened.

No measurements from this run have been inserted into `paper/PLaND.pdf` or its
source. CFPB and SpamAssassin collection have not started. The original run
directories, SOPs, candidate, logs, failed command and checkpoints remain intact
under `tmp/fresh-paper-20260905/`. `collection-hold.json` blocks controller
execution, resumption, stage completion, and normal paper-evidence packaging.

## Remaining source capacity

These counts come from the complete frozen official LEDGAR corpus, globally
deduplicated by normalized content, after excluding all recovered recorded
exposures and quarantining the interrupted final reservation. They are counts
of eligible source rows, not new model evaluations.

| Label | Official train | Official validation | Official test |
| --- | ---: | ---: | ---: |
| Governing Laws | 2,997 | 323 | 424 |
| Counterparts | 2,236 | 246 | 336 |
| Notices | 2,323 | 217 | 269 |
| Entire Agreements | 2,194 | 219 | 225 |
| Severability | 1,633 | 156 | 254 |
| Amendments | 1,348 | 92 | 72 |
| Survival | 1,324 | 80 | 68 |
| Assignments | 1,191 | 40 | 45 |
| Expenses | 1,094 | 7 | 32 |
| Terms | 1,029 | 0 | 26 |
| Required per label | 50 | 100 | 50 |

A fully untouched replacement cannot meet the approved official-partition
mapping. Merely changing the seed cannot create missing rows, and replacing
only the overlapping cases would not produce a fresh restart after selection
has already been observed.

## Smallest recovery decision

Keep exactly 500 development / 1,000 selection / 500 final-test cases, all ten
labels, the model, thresholds and gates. Amend only the LEDGAR sampling boundary
to create new balanced, disjoint splits from the untouched pooled source
partitions, or from untouched official training rows alone. There are sufficient
rows for either option. Such splits must be reported as newly sampled study
splits, not the official LEDGAR validation/test benchmark.

The operator has **not** made that amendment or generated replacement splits.
It needs explicit author approval because the current protocol requires
preserving the official boundaries. Any authorized restart must discard this
run's outputs as evidence, retain them as an invalid attempt, freeze a new
manifest, and construct/evaluate afresh without using its selection or test
outcomes for tuning.

## Audit artifacts and prevention

- `ledgar-freshness-incident.json`: source hashes, historical evidence pointers,
  3,796 recorded exposed IDs with normalized-content hashes, all 18 overlap IDs,
  quarantined final IDs, per-partition capacities and exact deficits.
- `datasets/scripts/audit_fresh_exposure.py`: deterministic corpus audit.
- `datasets/scripts/prepare_fresh_collection.py`: corrected to include
  aggregate-only paper pilots and interrupted fresh-run checkpoints.
- Regression checks: 17 dataset tests and six collection-controller tests pass.

This document is an incident/status report, **not** the requested final
paper-ready results report. Collection remains incomplete.
