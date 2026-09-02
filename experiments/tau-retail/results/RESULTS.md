# Tau-retail result

The frozen 20-case comparison completed locally, but it is a feasibility
failure rather than positive evidence for the PLaND hypothesis. Both SOPs
scored 0/20 because `qwen3:14b` never reached a normal stop inside the common
eight-step and 60-second bounds. The final-state evaluator assigns zero to
prematurely terminated trajectories, so no acceptable accuracy floor was
established.

| Measure | Natural-language SOP | Hybrid SOP |
| --- | ---: | ---: |
| Cases | 20 | 20 |
| Task success | 0.0% | 0.0% |
| Final-state correctness | 0.0% | 0.0% |
| Wall time | 450.89 s | 365.83 s |
| Mean case latency | 65.02 s | 52.94 s |
| Total measured tokens | 440,650 | 464,729 |
| Tool calls | 76 | 80 |
| Paid API cost | $0 | $0 |
| Ollama resource snapshot | 12 GB, 100% GPU | 12 GB, 100% GPU |
| Max-step terminations | 18 | 20 |
| Timeout terminations | 2 | 0 |
| SOP estimated tokens | 263 | 107 |
| SOP natural-language steps | 9 | 2 |
| SOP command/reference steps | 0 | 2 |

The hybrid run used 18.9% less wall time and 18.6% less mean case latency, but
5.5% more measured tokens. It is not an accepted optimization because neither
candidate solved a case.
Only one hybrid candidate was evaluated; further SOP evolution was stopped
before the ten-iteration cap because optimizing a zero-quality baseline would
not test the paper's preservation claim. A follow-up needs a locally runnable
model/harness combination that first produces non-zero baseline task success.

The raw JSON metrics and complete trajectories are stored beside this file.
Token totals are derived from per-message Ollama usage because this tau release
does not populate its run-level `agent_usage` or `user_usage` fields.
