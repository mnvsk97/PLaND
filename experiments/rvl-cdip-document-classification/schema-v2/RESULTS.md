# RVL-CDIP frozen-prompt experiment

## Question

Can PLaND convert an all-English document-classification SOP into a hybrid SOP
on a small RVL-CDIP subset while preserving at least 0.90 accuracy and reducing
aggregate model tokens?

## Frozen conditions

- Dataset: 32 OCR documents from an RVL-CDIP sampling mirror, 2 per class
- Development: one official validation example per class (16 cases)
- Validation: one official test example per class (16 cases)
- Selection seed: `20260902`; model seed: `42`
- OCR: local Tesseract 5.5.3, completed and hashed before baseline measurement
- Model: local Ollama `qwen3:14b`, temperature 0, reasoning disabled
- Accuracy floor: 0.90; primary objective: total tokens
- Minimum objective improvement: 5%; maximum candidates: 10
- Model, prompt, normalized harness, evals, scorer, datasource snapshot,
  permissions, and seeds were unchanged across comparable candidates

## Results

| Split | SOP | Accuracy | Total tokens | Mean latency | p95 latency |
| --- | --- | ---: | ---: | ---: | ---: |
| Development | Natural language | 87.50% (14/16) | 141,820 | 7.91 s | 12.76 s |
| Development | Hybrid candidate 003 | 93.75% (15/16) | 103,559 | 5.75 s | 8.84 s |
| Validation | Natural language | 81.25% (13/16) | 149,484 | 7.80 s | 12.50 s |
| Validation | Hybrid candidate 003 | 87.50% (14/16) | 98,115 | 5.53 s | 8.90 s |

On development, candidate 003 improved accuracy by 6.25 percentage points,
reduced tokens by 38,261 (26.98%), and reduced mean latency by 2.16 seconds
(27.36%). On validation it also improved accuracy by 6.25 points, reduced
tokens by 51,369 (34.36%), and reduced mean latency by 2.28 seconds (29.17%).

Candidate 003 was nevertheless **rejected** because validation accuracy was
0.875, below the frozen 0.90 floor. PLaND therefore reports no accepted hybrid
for this subset. The result is informative but not a successful replication of
the Tobacco-3482 acceptance result.

## Evolution record

1. Candidate 001 added text compaction and structural metadata. It was rejected
   before validation because accuracy stayed at 0.875 and tokens increased.
2. Candidate 002 used a compact head/tail view. Its first run exposed an
   unapproved tool name; after preserving the scorer and using the approved
   tool interface, it reached 0.9375 raw development accuracy but emitted one
   invalid label and was rejected before validation.
3. Candidate 003 kept bounded head/tail trimming and added a closed-label guard.
   It passed development but failed the validation accuracy floor.

No further candidate was generated from validation failures because the
validation labels are held out from evolution. Although seven iteration slots
remained, using those failures to tune another candidate would contaminate the
validation split.

## Caching and parallelism decision

The evolver explicitly checked both opportunities. Caching was not used because
each case reads a unique document once, so there is no stable repeated work to
reuse during a candidate run. Parallel execution inside the SOP was not used
because each classification has one datasource operation followed by a semantic
decision; those steps are dependent. Evaluation cases could be scheduled in
parallel by a future runner experiment, but doing so here would change resource
contention and make latency incomparable with the frozen sequential baseline.

## Evidence boundary

This is a deliberately small 32-document study with one example per class per
split, one OCR engine, one model, and one seed. The sampling mirror contains
only 1,600 RVL-CDIP examples. These results do not estimate full RVL-CDIP
accuracy and should not be compared with models evaluated on all 40,000 test
images. Raw images, OCR, eval rows, and traces remain under ignored `tmp/` paths;
committed comparison and decision files retain aggregate metrics, SOP snapshots,
and frozen fingerprints.
