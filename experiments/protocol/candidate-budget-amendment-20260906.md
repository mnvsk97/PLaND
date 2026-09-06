# Author-approved candidate-budget amendment

Recorded 2026-09-06 UTC, relayed by source task `01a0743c-35f8-7d60-9a0d-165e3127862a`.

This amends only the candidate budget in [the original protocol](fresh-paper-collection.md). The original protocol and original dataset JSON plans remain immutable, with their original hashes retained in the operations history.

Allow up to ten hybrid candidate attempts per dataset, using development inputs and traces only. Preserve every rejected attempt. Stop at the first candidate satisfying the existing development readiness requirements, freeze it, and expose exactly that one candidate once to the 1,000-case selection split. A selection rejection ends the dataset; selection observations cannot feed another candidate. If all ten candidates fail development readiness, end as `candidate_nonviable`, with selection and final test unopened. Final test still requires selection acceptance.

The ten English-baseline attempts, 500/1,000/500 splits, evaluated model/runtime, statistical gates, repeat protocol, and paper claim scope are unchanged. LEDGAR remains complete: its first candidate qualified, so the increased maximum does not require another attempt. CFPB resumes after its ninth English development attempt (75.0%); no candidate or held-out evaluation had begun when this amendment was recorded. SpamAssassin has not begun.
