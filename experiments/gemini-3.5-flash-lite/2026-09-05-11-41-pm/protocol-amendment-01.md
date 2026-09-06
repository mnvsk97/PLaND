# Protocol amendment 01: one-for-one provider-block replacements

Authorized by the user on 2026-09-06 after the frozen SpamAssassin selection
case `mail-3125dcdc7726abc1c128` was returned three times as
`PROHIBITED_CONTENT` by the sole approved provider endpoint.

This amendment affects only the SpamAssassin selection split. A required case
that the frozen provider terminally blocks is replaced by the next eligible,
previously unopened case of the same reference label under the original seeded
ranking. The replacement must have a unique identifier and unique normalized
sanitized content relative to every prior and current study case. The split
remains exactly 1,000 cases and balanced 500 ham / 500 spam.

After every replacement, both paired arms restart on the complete amended
selection split for all three frozen repeat seeds and in the original arm
order. Partial results from the superseded selection are preserved but never
pooled. The baseline SOP, candidate package, model identity, endpoint, runtime,
workers, statistical gates, development evidence, and final-test split remain
unchanged. Final test remains sealed until all three amended selection pairs
pass the original release gate.

Effective boundary: after commit `4b909eb4`, which preserves the original
provider-blocked attempt and its terminal selection assessment.
