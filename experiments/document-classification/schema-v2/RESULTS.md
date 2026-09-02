# Frozen-prompt schema-v2 experiment

## Question

Can a natural-language document-classification SOP be changed into a genuinely
hybrid SOP while keeping accuracy above 0.90 and reducing aggregate model
tokens, with the system prompt and all non-SOP experiment boundaries frozen?

## Frozen conditions

- Model: local Ollama `qwen3:14b`
- Model digest: `bdbd181c33f2ed1b31c972991882db3cf4d192569092138a7d29e973cd9debe8`
- Temperature: 0; seed: 42; reasoning: disabled
- Cases: 10 development and 10 validation
- Primary objective: `total_tokens`
- Minimum objective improvement: 5%
- Accuracy floor: 0.90
- Maximum candidate attempts: 10
- System prompt, normalized agent harness, datasource snapshot, eval CSV,
  scorer, execution permissions, model, and seed: frozen

The saved development and validation comparisons contain the exact frozen
fingerprints. The system prompt was generated once before baseline measurement
and did not change.

## SOP representations

| Version | English | Reference | Command | Variant |
| --- | ---: | ---: | ---: | --- |
| Baseline | 5 | 0 | 0 | Natural language |
| Candidate 001 | 4 | 0 | 1 | Hybrid |

Candidate 001 replaces raw document reading with a deterministic, bounded
Python command. Short OCR text is preserved. Long text retains a fixed-size
head and tail plus structural metadata. Semantic label selection remains in
English.

## Results

| Split | SOP | Accuracy | Total tokens | Mean latency | p95 latency | Model cost |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Development | Natural language | 100% (10/10) | 111,452 | 10.43 s | 24.78 s | $0 |
| Development | Hybrid | 100% (10/10) | 90,930 | 8.87 s | 10.56 s | $0 |
| Validation | Natural language | 100% (10/10) | 117,259 | 11.68 s | 24.74 s | $0 |
| Validation | Hybrid | 100% (10/10) | 89,942 | 8.98 s | 10.94 s | $0 |

On validation, the hybrid SOP preserved accuracy, reduced aggregate tokens by
27,317 (23.30%), and reduced mean latency by 2.71 seconds (23.16%). On
development, it reduced tokens by 20,522 (18.41%) and mean latency by 1.56
seconds (15.00%). The deterministic assessor accepted candidate 001 with no
failed checks. Optimization stopped after one iteration because the success
condition had been reached; running nine unnecessary candidates would add
experiment cost without serving the configured objective.

## Evidence boundary

This is a small proof-of-concept with one case per class per split, one model,
one seed, no third held-out split, and no repeated trials. It supports the
mechanistic claim that this accepted hybrid SOP reduced measured expense under
the recorded conditions. It does not estimate population accuracy or establish
general performance across datasets, models, or seeds.

Raw case traces and OCR remain under ignored `tmp/` paths. Safe aggregate
evidence is stored in `comparisons/` and `decisions/`.
