# Frozen hosted collection protocol

Run LEDGAR, CFPB, and SpamAssassin in that order using the exact model and
runtime recorded in `plan.json`. Build new 500-case development, 1,000-case
selection, and 500-case final-test splits from locked source bytes while
excluding every previously opened case ID and normalized-content duplicate.

For each dataset, allow at most ten English-baseline development attempts and
at most ten hybrid development attempts. Stop at the first development-ready
baseline and first development-ready hybrid. Preserve every failed and rejected
attempt. Only one frozen hybrid may enter selection, and selection rejection is
terminal. Never open final test unless selection accepts the candidate.

Run three paired baseline/hybrid executions for each reached split. Across all
three splits this is 12,000 planned case evaluations per dataset: 2,000 cases,
two arms, and three executions. A command-resolved hybrid case remains a case
evaluation but does not make a model call.

Require accuracy of at least 80%, a candidate accuracy difference no worse than
-2 percentage points, at least 5% token reduction with a positive bootstrap
interval lower bound, 5,000 bootstrap samples, and zero execution errors. Keep
the model endpoint fixed with provider fallbacks disabled.

Treat HTTP 429 responses as capacity signals, not experiment failures. Record
each rate-limit event, honor `Retry-After` when supplied, otherwise use bounded
exponential backoff with case-specific jitter, and retry until the case succeeds
or the operator explicitly stops the process. Do not change the model, provider,
endpoint, or routing policy to escape a rate limit.

Record case outputs, correctness, tokens, cost, latency, provider receipts,
runtime settings, SOP/package hashes, source hashes, commands, logs, decisions,
and failures. Generate an evidence manifest and audit it before changing paper
numbers. Make only evidence-required manuscript edits after all three datasets
reach valid terminal states.
