# Enterprise benchmark results

This file summarizes the completed PLaND pilot experiments. Each upstream
dataset was frozen at up to 100 cases. The measured paper subsets contain 20
cases selected before model execution. All runs used local Ollama
`qwen3:14b`, seed `20260902`, no paid API, and frozen prompts, harnesses,
scorers, data, expected outputs, and execution permissions.

These are paired pilot results, not population-level benchmark estimates. Raw
or redistributable artifacts are retained in each experiment directory;
restricted or bulky source data remains reproducible through `datasets/` and
is not committed.

## Outcome summary

| Workflow | NL quality | Hybrid quality | NL tokens | Hybrid tokens | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| LEDGAR contract classification | 85% accuracy; 0.813 macro F1 | 85%; 0.813 | 6,986 | 3,173 (-54.6%) | Accepted |
| CFPB complaint routing | 60% accuracy; 0.583 macro F1 | 60%; 0.583 | 11,724 | 7,479 (-36.2%) | Accepted |
| SpamAssassin email classification | 90% accuracy; 0.899 macro F1 | 85%; 0.847 | 52,250 | 44,270 (-15.3%) | Meets 75% floor; held-out regression |
| tau-retail tool workflow | 0% task success | 0% | 440,650 | 464,729 (+5.5%) | Feasibility failure |
| SROIE frozen OCR | 0.868 field F1 | 0.864 | 16,295 | 15,109 (-7.3%) | Rejected on validation quality |
| SROIE end to end | 0.200 field F1 | 0.178 | 18,487 | 17,338 (-6.2%) | Nonviable OCR baseline; rejected |

The prior RVL-CDIP/Tobacco robustness experiment remains a negative result:
its strongest hybrid improved validation accuracy from 81.25% to 87.50% and
reduced tokens by 34.36%, but it stayed below the preregistered 90% quality
floor and was rejected.

## Interpretation boundary

The LEDGAR and CFPB pilots support the narrow hypothesis that deterministic
SOP steps can bypass some model calls while preserving measured classification
quality. They do not establish that every workflow can be optimized this way.

SpamAssassin is weaker evidence: it meets its preregistered absolute quality
floor and reduces tokens, but hybrid accuracy is five points below NL overall
and 25 points below NL on the four-case test. It is retained as a transparent
threshold result rather than grouped with the equal-accuracy text results.

The other experiments identify two important boundaries:

- A workflow cannot demonstrate quality-preserving optimization when the local
  baseline never completes a task, as in tau-retail.
- An OCR-dominated pipeline must first reach a viable perception baseline. In
  end-to-end SROIE, Tesseract word error rate was 0.871 and validation field F1
  was zero.

Text-run latency overlapped other Ollama workloads and is therefore retained
for audit but excluded from causal claims. Tau and SROIE measurements should
also be interpreted as single-machine pilot measurements rather than general
hardware performance.

## Detailed artifacts

- `ledgar-text-classification/`
- `cfpb-text-classification/`
- `spamassassin-email-classification/`
- `tau-retail/`
- `sroie-receipt-extraction/`
- `rvl-cdip-document-classification/schema-v2/`
