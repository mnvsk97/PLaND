# ledgar-text-classification three-run variance evidence

This folder contains three new paired replications under the frozen optimized
runtime. These runs are descriptive replication evidence, not new untouched tests.
The original sequential results are not pooled because runtime conditions differ.

## Summary

- Cases per run: 1000
- Seeds: 20260903, 20260904, 20260905
- NL accuracy mean (sample SD; range): 0.9370 (0.0000; 0.9370-0.9370)
- Hybrid accuracy mean (sample SD; range): 0.9290 (0.0000; 0.9290-0.9290)

With only three seeds, these values characterize the observed frozen condition;
they do not support a significance or broad generalization claim.

## Reproduce and inspect

Run `experiments/variance-study/run_variance_study.py` using the exact command in
`experiments/variance-study/README.md`. `run-ledger.json` records each expanded
command, order, start/end timestamp, exit status, and log checksum. Each
`seed-*-nl.json` or `seed-*-hybrid.json` stores per-case prediction, correctness,
tokens, latency, and routing source. Each paired comparison applies the frozen
absolute viability, non-inferiority, and efficiency gates.

`manifest.json` gives the byte size and SHA-256 checksum of every artifact in this
folder. Prepared source text stays in ignored `tmp/`; the content audit recorded in
the cross-study summary confirms that committed JSON contains no source-text fields.
