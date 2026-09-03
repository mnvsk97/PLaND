# Optimized Ollama recollection, 2026-09-02

This post-change replication reran the existing frozen text-classification skills; it did not regenerate or re-evolve those skills with the generalized generator. Raw case artifacts are retained locally under `tmp/recollection-20260902/` and are not substituted for the original untouched confirmatory release.

## Frozen runtime

- Hardware: Apple M5 Pro, 18 CPU cores, 48 GB unified memory
- Ollama: 0.33.0
- Model: `qwen3:14b`
- Model digest: `bdbd181c33f2ed1b31c972991882db3cf4d192569092138a7d29e973cd9debe8`
- Request settings: thinking off, streaming off, temperature 0, seed 20260902, context 4,096, maximum output 128, exact JSON schema, model retained in memory
- Server settings: Flash Attention on, q8_0 KV cache, one loaded model, two parallel requests
- Gate: minimum accuracy 0.80, paired non-inferiority margin 0.02, minimum token reduction 0.05 with positive lower bootstrap limit

## Results

| Dataset and split | NL accuracy | Hybrid accuracy | NL tokens | Hybrid tokens | Token reduction | Accuracy-difference 95% CI | Decision |
|---|---:|---:|---:|---:|---:|---:|---|
| LEDGAR validation, 100 | 93% | 94% | 37,148 | 21,104 | 43.19% | [-2, +5] points | Pass |
| CFPB validation, 100 | 78% | 71% | 58,372 | 33,120 | 43.26% | [-13, -2] points | Reject |
| SpamAssassin validation, 100 | 88% | 84% | 188,384 | 178,881 | 5.04% | [-9, +1] points | Reject |
| LEDGAR test replication, 1,000 | 93.7% | 92.9% | 376,090 | 225,575 | 40.02% | [-1.6, 0.0] points | Pass |

The LEDGAR test replication bypassed 411 model calls. Its NL and hybrid elapsed collection times were 586.13 and 367.72 seconds respectively. Because requests overlapped, elapsed collection time is a throughput measure and must not be compared directly with the original sequential per-case latency.
