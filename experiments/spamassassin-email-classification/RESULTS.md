# SpamAssassin experiment results

## Scope

The preparer froze 100 unique sanitized emails, balanced between spam and ham,
with a `60/20/20` split. The measured subset contains 20 emails, balanced within
each `12/4/4` development, validation, and test split. All runs used local
Ollama `qwen3:14b`, seed `20260902`, and no paid API.

Headers and subject markers that directly revealed a SpamAssassin decision were
removed before deterministic selection. Candidate 001 was written using only
the task definition, label names, and development evidence. It was accepted on
validation and the test split was run once afterward.

## Results

| Split | NL accuracy | Hybrid accuracy | NL tokens | Hybrid tokens | Deterministic cases |
| --- | ---: | ---: | ---: | ---: | ---: |
| Development | 83.3% | 83.3% | 27,108 | 21,229 | 3/12 |
| Validation | 100% | 100% | 18,906 | 18,810 | 0/4 |
| Test | 100% | 75% | 6,236 | 4,231 | 1/4 |
| All cases | 90% | 85% | 52,250 | 44,270 | 4/20 |

Across all cases, tokens fell by 15.27% and model calls fell from 20 to 16.
Accuracy fell by five percentage points. The hybrid meets the predeclared 75%
absolute quality floor on held-out test, so it is accepted under the configured
decision rule. It does **not** preserve the NL test score, and the test contains
only four messages. This should be reported as threshold-level pilot evidence,
not as proof of equivalent spam-filtering accuracy.

## Limitations

- The source email is from 2002-2003 and does not represent modern phishing,
  malware, or business-email compromise.
- Twenty measured cases, including four test cases, produce wide uncertainty.
- Sanitization removes direct label leaks but cannot remove every historical
  corpus artifact.
- Deterministic rules cover only high-precision patterns and are not a
  production spam engine.
