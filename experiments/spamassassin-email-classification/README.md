# SpamAssassin email-classification experiment

This experiment classifies complete RFC-822 messages as `spam` or `ham`.
Preparation removes corpus and filter headers that directly reveal the label,
deduplicates sanitized messages, and freezes 100 balanced cases (`60/20/20`).
The paper comparison uses a predeclared balanced 20-case subset (`12/4/4`).

The system prompt, Ollama model and digest, seed, eval CSV, selection, scorer,
harness, and execution permissions are frozen across variants. Evolution may
change only the SOP and its directly invoked classifier. Rules must be authored
from development evidence only. Validation determines acceptance; test is run
once afterward.

The corpus is from 2002-2003. Results test the PLaND mechanism on historical
email and must not be presented as production performance on current phishing,
malware, or business-email compromise.

## Confirmatory dataset

The prepared confirmatory design supersedes the pilot for inference:
100 development, 100 validation, and 1,000 untouched emails, with equal spam
and ham counts in every split. `confirmatory-dataset.json` records immutable
hashes and links to `datasets/proofs/spamassassin-confirmatory.json`. The data
audit passed, including a byte-identical repeat preparation.
All pilot IDs and normalized sanitized-message contents are excluded from every
new split.

The 100-case validation comparison is complete. NL accuracy was `90%` and
hybrid accuracy was `86%`; tokens fell from `238,077` to `228,359` (`4.08%`).
The paired accuracy-difference interval was `[-9, +1]` percentage points and
the token-reduction interval was `[1.02%, 8.50%]`. The candidate failed the
two-point non-inferiority gate and the minimum `5%` token-reduction gate, so the
1,000-case test was not released. See `results/confirmatory-validation-*.json`.

## Pilot result

Candidate 001 preserved development accuracy (`83.3%`) and validation accuracy
(`100%`) while reducing tokens. On the one-time held-out test, however, accuracy
was `100%` for NL and `75%` for hybrid. The hybrid exactly meets the
predeclared `75%` floor, but the four-case test is too small to treat that
threshold result as strong evidence of generalization. See `RESULTS.md`.
