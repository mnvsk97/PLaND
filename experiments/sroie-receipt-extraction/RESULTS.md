# SROIE PLaND experiment results

## Scope

The preparer froze 100 receipts (`60/20/20`). The hypothesis run used a
deterministic 20-case subset (`12/4/4`) with local Ollama `qwen3:14b` and local
Tesseract 5.5.3. The system prompt, model digest, seed, harness/scorer,
datasource snapshot, selected cases, expected outputs, and permissions are
hashed in every result. Local-model cost is recorded as `$0.00`; token, latency,
and process-memory measurements capture the actual expense proxies.

The first hybrid attempt pruned OCR evidence and showed an immediate quality
regression on development, so it was stopped. Candidate 002 uses a lossless
Python normalization step and a shorter hybrid SOP. It was evaluated once on
validation and was not revised from validation or test outcomes. Although the
runner records test traces for audit completeness, no test result contributed
to candidate construction or acceptance.

## Results

| OCR mode | SOP | All-case field F1 | Document exact | Tokens | Mean total latency | OCR WER |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Frozen | NL baseline | 0.868 | 25% | 16,295 | 14.85 s | 0.000 |
| Frozen | Hybrid candidate 002 | 0.864 | 20% | 15,109 | 13.96 s | 0.000 |
| Tesseract end to end | NL baseline | 0.200 | 0% | 18,487 | 11.55 s | 0.871 |
| Tesseract end to end | Hybrid candidate 002 | 0.178 | 0% | 17,338 | 10.13 s | 0.871 |

On frozen OCR, the hybrid reduced tokens by 7.28% and mean latency by 6.01%,
but validation field F1 fell from 0.746 to 0.715. It was therefore **rejected**:
the expense improvement did not preserve the quality floor.

The end-to-end validation baseline had field F1 0.000 and OCR WER 1.000. A
candidate cannot meaningfully pass by preserving zero quality, so a minimum
viable baseline field-F1 gate of 0.50 rejects this track as **not optimizable**.
Across all 20 end-to-end cases, Tesseract WER was 0.871 and NL field F1 was only
0.200. This directly supports reporting frozen-OCR and end-to-end results
separately: OCR dominates the deployable pipeline on these low-resolution
images.

## LiteParse replication

A separate replication used local LiteParse 2.14.3 with its bundled Tesseract
OCR, English language data, 300 DPI, and two workers. It used the same 20
receipts, model digest, seed, system prompt, SOPs, expected outputs, scorer, and
execution permissions. The original Tesseract result files were not replaced;
the LiteParse traces and metrics are stored under `results/liteparse/`.

| OCR mode | SOP | All-case field F1 | Document exact | Tokens | Mean total latency | OCR WER |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| LiteParse end to end | NL baseline | 0.309 | 5% | 9,889 | 2.68 s | 0.715 |
| LiteParse end to end | Hybrid candidate 002 | 0.297 | 5% | 8,696 | 2.57 s | 0.715 |

Compared with the earlier direct-Tesseract NL run, LiteParse reduced OCR WER
from 0.871 to 0.715 and raised all-case field F1 from 0.200 to 0.309. The
LiteParse hybrid used 12.06% fewer tokens and had 4.31% lower mean total
latency than the LiteParse NL baseline. On validation, however, the NL baseline
field F1 was only 0.170, below the predeclared minimum viable value of 0.50.
The hybrid validation field F1 was 0.173. It preserved relative quality and
reduced validation tokens from 2,056 to 1,820, but the assessment correctly
rejects the result as **not optimizable** because the baseline is not viable.

This result proves that LiteParse can process the SROIE images and can improve
the OCR signal without a paid service. It does not establish that the resulting
end-to-end receipt extractor is accurate enough for deployment or SOP
optimization.

## Relation to the existing Tobacco/RVL robustness experiment

The existing 32-document RVL-CDIP/Tobacco-style run also used frozen local
Tesseract OCR. Its strongest hybrid improved validation accuracy from 81.25%
to 87.50%, reduced tokens by 34.36%, and reduced mean latency by 29.17%, but was
rejected against its predeclared 90% accuracy floor. Both multimodal studies
therefore report useful efficiency signals but **no accepted hybrid**. SROIE
additionally shows why OCR quality must be isolated before attributing changes
to SOP evolution.

## Stopping decision

Two of the ten allowed candidate slots were used. Evolution stopped because
candidate 002 had already consumed validation and failed its quality floor;
creating further candidates from that failure would tune to the held-out
validation set. Seven unused candidate slots are not evidence of a successful
optimization. The final outcome is a clean negative result, not an accepted
hybrid.
