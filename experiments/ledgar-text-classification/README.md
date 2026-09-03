# LEDGAR text-classification experiment

Classifies contract provisions into ten labels. The confirmatory dataset has 100
development, 100 validation, and 1,000 test clauses, balanced by label and kept
within official LexGLUE train/validation/test boundaries. Pilot IDs and matching
normalized content are excluded. See `confirmatory-dataset.json` and
`datasets/proofs/ledgar-confirmatory.json`.

The model/digest, prompt, seed, data, scorer, harness, runtime, and permissions
are frozen. Only the SOP and its classifier may change; rules use development
evidence only. Run the shared text runner once with `nl/SKILL.md` and once with
`hybrid/SKILL.md` plus `hybrid/classify.py`.

## Results

Validation passed: accuracy was 92% NL versus 93% hybrid, with a paired
difference interval of [-2, +5] points. Tokens fell 43.19%, from 37,147 to
21,104, so the test was released once.

On 1,000 test clauses, accuracy was 93.5% NL versus 92.7% hybrid; the -0.8-point
difference had interval [-1.6, 0.0], within the two-point margin. Tokens fell
40.02% (376,088 to 225,573), and model calls fell from 1,000 to 589. The result
passed relative quality, absolute quality, and token gates.

The optimized replication produced 93% versus 94% validation accuracy and 93.7%
versus 92.9% test accuracy, with the same 411-call bypass and 40.02% test token
reduction. Because test cases were previously used, this is replication—not a
new confirmatory release.

Artifacts are `results/confirmatory-*.json` and
`results/replication-20260902-*.json`. Raw clauses and traces stay under
ignored `tmp/`. Latency is machine- and concurrency-specific; token and call
counts remain paired.
