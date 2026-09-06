# Protocol amendment 02: cumulative one-for-one provider-block replacements

Authorized under the user's standing instruction on 2026-09-06 that every
provider-blocked content item be replaced by another item that passes through,
without reducing the dataset size.

The first amended SpamAssassin selection lineage removed
`mail-3125dcdc7726abc1c128`. During its restarted baseline selection run, the
sole approved provider endpoint terminally returned `PROHIBITED_CONTENT` for a
second selection case, `mail-449598896e25273135c3`. A compatibility screen of
the entire 1,000-case amended selection split combined the 636 completed cases
with direct screening of the remaining 364 and found no other terminal provider
blocks in that split.

This amendment removes the second blocked case and replaces it with the next
eligible, previously unopened case of the same reference label under the
original seeded reserve ranking. The first replacement remains in place. The
new replacement must be explicitly screened against the frozen provider before
paired selection begins. If that replacement is blocked, it is preserved and
superseded by another recorded amendment rather than counted as a failed case.

The selection split remains exactly 1,000 cases and balanced 500 ham / 500
spam. Both paired arms restart on the complete newly amended selection split
for all three frozen repeat seeds and in the original arm order. Superseded
partial results remain preserved and are never pooled. The baseline SOP,
candidate package, model identity, endpoint, runtime, eight-worker ceiling,
statistical gates, development evidence, and 500-case final-test split remain
unchanged. HTTP 429 responses continue to be retried until available and are
not classified as run failures. Final test remains sealed until every amended
selection gate passes.

Effective boundary: after commit `dd136cd3`, which preserves the first amended
lineage, its second provider block, its full-split compatibility screen, and its
terminal superseded assessment.
