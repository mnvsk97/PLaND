# Optimized Ollama replication, 2026-09-02

This reran the frozen text-classification skills; it did not regenerate or
re-evolve them. Raw runs remain under ignored `tmp/recollection-20260902/`.
Previously evaluated LEDGAR test cases make this replication evidence, not a new
confirmatory release.

## Runtime

- Apple M5 Pro, 48 GB; Ollama 0.33.0; `qwen3:14b`
- Digest: `bdbd181c33f2ed1b31c972991882db3cf4d192569092138a7d29e973cd9debe8`
- Temperature 0; seed 20260902; thinking/streaming off; context 4,096; output
  cap 128; exact JSON schema; retained model
- Flash Attention; q8_0 KV cache; one loaded model; two parallel requests
- Gate: accuracy >= 0.80; paired margin 0.02; token reduction >= 5% with a
  positive bootstrap lower bound

## Results

| Dataset and split | NL -> hybrid accuracy | NL -> hybrid tokens | Difference 95% CI | Decision |
| --- | ---: | ---: | ---: | --- |
| LEDGAR validation (100) | 93% -> 94% | 37,148 -> 21,104 (-43.19%) | [-2, +5] points | Pass |
| CFPB validation (100) | 78% -> 71% | 58,372 -> 33,120 (-43.26%) | [-13, -2] | Reject |
| SpamAssassin validation (100) | 88% -> 84% | 188,384 -> 178,881 (-5.04%) | [-9, +1] | Reject |
| LEDGAR test (1,000) | 93.7% -> 92.9% | 376,090 -> 225,575 (-40.02%) | [-1.6, 0.0] | Pass |

LEDGAR bypassed 411 model calls. NL and hybrid collection took 586.13 and 367.72
seconds, but overlapping requests make these throughput—not sequential
latency—measurements.
