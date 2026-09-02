# Document classification experiment results

> Follow-up: a frozen-system-prompt schema-v2 experiment subsequently accepted
> a genuinely hybrid SOP with 100% validation accuracy, 23.30% fewer tokens,
> and 23.16% lower mean latency. See [`schema-v2/RESULTS.md`](schema-v2/RESULTS.md).

## Fixed conditions

- Dataset: QS-OCR-Small v1.0 with the Tobacco3482 audit annotations.
- Cases: 10 development and 10 validation, one case per class in each split.
- Model: local Ollama `qwen3:14b`.
- Model digest: `bdbd181c33f2ed1b31c972991882db3cf4d192569092138a7d29e973cd9debe8`.
- Model settings: temperature 0, seed 42, reasoning disabled.
- Estimated model-service cost: USD 0 for every run.
- Target accuracy: 0.90.
- Validation mean-latency guardrail: no more than 2.0 times the initial agent.
- Validation token guardrail: no regression from the initial agent.

Token counts are the sum of usage reported for every model call in an agent
case. Because an agent resends accumulated context on later turns, these are
billed-style aggregate tokens rather than unique document tokens.

## Initial versus accepted agent

| Split | Agent | Accuracy | Total tokens | Mean latency | p95 latency |
| --- | --- | ---: | ---: | ---: | ---: |
| Development | Initial | 90% (9/10) | 340,427 | 13.67 s | 56.74 s |
| Development | Accepted | 100% (10/10) | 86,989 | 22.96 s | 38.50 s |
| Validation | Initial | 100% (10/10) | 173,222 | 11.31 s | 16.09 s |
| Validation | Accepted | 100% (10/10) | 92,839 | 12.78 s | 26.48 s |

Relative to the initial agent, the accepted agent reduced aggregate tokens by
74.45% on development and 46.40% on validation. Development accuracy increased
by 10 percentage points; validation accuracy was unchanged. Mean latency rose
67.91% on development and 13.04% on validation. Development p95 latency fell
because the accepted harness removed a repeated write-tool loop, while
validation p95 latency increased.

## Evolution decisions

| Candidate | Change | Development accuracy | Token ratio vs. initial | Decision |
| --- | --- | ---: | ---: | --- |
| 001 | Deterministic signal extraction plus read-only filesystem | 70% | 22.63% | Rejected: accuracy regression and errors |
| 002 | Read-only filesystem middleware | 80% | 23.96% | Rejected: accuracy regression and invalid JSON |
| 003 | Remove unused filesystem tools and default subagent | 80% | 15.62% | Rejected: accuracy regression |
| 004 | Candidate 003 plus email/form/letter precedence | 100% | 25.55% | Accepted after validation |

Candidate 001 is important negative evidence: converting cue identification to
deterministic counts was inexpensive but caused the model to over-weight weak
surface signals. PLaND therefore rejected this attempted compilation. The
accepted change retained semantic classification in English, narrowed the
harness tool surface, and added only the decision boundary supported by
development failures.

## Accepted change

The accepted agent:

1. disables DeepAgents' default general-purpose subagent;
2. hides write, edit, delete, execute, search, glob, and listing tools;
3. retains `read_file` for progressive skill loading and `read_datasource` for
   approved documents;
4. adds precedence rules distinguishing email and form structures from letters.

The model, dataset, expected outputs, scorer, seed, and datasource manifest did
not change.

## SOP representation status in this original run

The initial SOP has four explicitly marked English steps. The accepted SOP has
five explicitly marked English steps and no command step. The accepted system
is hybrid at the agent boundary—deterministic datasource tools and harness
restrictions surround natural-language classification—but it is not evidence
of a successful English-to-command SOP conversion. The only command-oriented
candidate regressed accuracy and was rejected. Consequently, the recorded run
supports initial-versus-constrained-agent metrics, not a natural-language-SOP
versus hybrid-SOP claim. Future runs now snapshot the exact SOP and save a
dedicated NL-versus-hybrid comparison only when at least one command step
survives acceptance.

## Scope

This is a complete small-scale proof-of-concept, not a paper-grade estimate of
population accuracy. It has 20 audited cases, one run per agent/split, no held-
out set, no repeated seeds, and no confidence interval. The results support
claims about this execution and expose useful mechanisms, but do not establish
general performance across tasks, models, or document distributions.
