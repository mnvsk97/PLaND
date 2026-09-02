# Run contract

Use separate development, validation, and held-out sets for experiments intended to support general claims. Development traces guide changes, validation selects candidates and triggers successful stopping, and held-out data is evaluated once at the end. A small proof-of-concept may explicitly omit held-out data only when the report labels the result preliminary, avoids generalization claims, and records that limitation.

Store each case's stable identifier, actual output, trace, latency, input and output tokens, estimated model and service cost, error classification, and score. Store each iteration's candidate snapshot, hypothesis, aggregate metrics, and accept/reject decision.

Before the baseline, save hashes for the generated system prompt, normalized agent harness, datasource manifest entries, eval CSV, and scorer implementation. The eval hash may be named `evaluation_sha256` or `evals_sha256`; consumers must normalize those aliases and reject missing or conflicting values. Candidates may change SOP tool wiring, but the normalized harness fingerprint must ignore only that allowed wiring and reject every other harness change. Missing fingerprints make runs incomparable.

Every run artifact must also contain the exact SOP text, its SHA-256 hash, and counts of `english`, `reference`, and `command` steps. Mark every numbered SOP step explicitly with `<!-- pland:english -->`, `<!-- pland:reference -->`, or `<!-- pland:command -->`; do not infer the research variable from prose after the run.

For an accepted hybrid candidate, save a machine-readable comparison against the initial natural-language SOP on the same split. Preserve absolute and delta values for accuracy, correct/case counts, input/output/total tokens, estimated model cost, and total/mean/p95 wall-clock latency. Reject comparisons when model, model digest, seed, eval path, or split differs. The comparison file is part of the required experiment record.

Number candidate iterations from 1. Configure `max_iterations` before the first candidate, defaulting to 10, and keep it fixed for the run. Iteration 10 is permitted when the default is used; iteration 11 is not. Reaching the limit stops the search without converting the best-so-far candidate into a success.

Configure one primary expense objective before the baseline: aggregate tokens, mean wall-clock latency, or estimated model cost. Accuracy is a floor. A candidate above the accuracy floor is eligible only when it improves the primary objective by the configured minimum ratio and satisfies all secondary guardrails. A zero minimum still requires strict improvement; equality is not improvement. Final acceptance requires both baseline and candidate validation artifacts on the same frozen evaluation set. Reaching the accuracy floor without improving the expense objective is not success.

Use accuracy or F1 for classification, field-level checks for extraction, and final-state verification for workflows. Use an LLM judge only for semantic properties that deterministic checks cannot settle. A judge or infrastructure failure is not an agent failure.

Every command step needs an explicit input/output contract, useful errors, focused success and failure checks, declared dependencies, and recorded network destinations. Unit checks are necessary but do not establish safe compilation without end-to-end validation evidence.
