# Approved LEDGAR-only restart from untouched training rows

On 2026-09-05 the author was asked: “May we use only untouched rows from the
official LEDGAR training partition to create new balanced 500 development /
1,000 selection / 500 final-test study splits?” The author answered:
“sure, lets only do ledgar for now”. Approval is recorded in source task
`01a0743c-35f8-7d60-9a0d-165e3127862a`, turn
`01a0749a-161d-7692-a917-d51ab3e447ad`.

This supersedes only the LEDGAR official-partition mapping and the three-dataset
execution scope in `fresh-paper-collection.md`. That original approved protocol
remains immutable. All thresholds, label scope, model/runtime, scientific gates,
construction limits, evidence requirements, and paper claim boundaries remain.

## Frozen sampling and scope

- LEDGAR only; do not start CFPB or SpamAssassin.
- Use the existing locked LEDGAR source bytes, but sample only official `train`
  rows. Preserve the paper's ten labels and exclude every historically opened
  ID and normalized-content duplicate, including the earliest paper pilot and
  all 2,000 rows reserved by the invalid first collection.
- Globally deduplicate source content before sampling. Rank eligible training
  rows per label by SHA-256 of `20260902:id`. Take the lowest 200 per label;
  assign the first 50 to development, next 100 to selection, final 50 to test.
- Freeze all splits together: exactly 500 development / 1,000 selection /
  500 final test. These are newly sampled study splits, not official LEDGAR
  validation/test benchmark scores.
- Preserve the invalid collection and its hold/incident. Create new packages,
  runs, manifests and report from zero. Reuse no invalid predictions, rules or
  measured outputs; do not tune against any prior selection/test observations.

## Unchanged experiment contract

Generate the English baseline through `generate-initial-version`, using only
the task contract and development inputs. Evaluate development and allow at most
ten English-only attempts until accuracy is at least 80%, normal completion is
100%, and no execution errors remain. Stop as nonviable if the limit is reached.
After readiness, `pland-evolver` may construct one hybrid candidate using only
new development inputs and traces. Preserve every version and the complete
exact English fallback. Reject on development if quality or expense objectives
fail; do not manufacture another candidate.

Compare the frozen baseline and candidate on identical selection cases, model,
digest, prompt, runner, scorer, runtime, seed and permissions. Require both
accuracies >=80%, the paired 95% accuracy-difference bootstrap lower endpoint
>=-0.02, token reduction >=5%, its paired 95% lower endpoint >0, and no
unaccounted errors. Use 5,000 bootstrap samples and seed 20260902.

Open final test only after recorded selection acceptance. Report its paired
outcome regardless of success; never retune. Run three additional paired
executions on the final test if accepted, otherwise selection, with inference
seeds 20260903/20260904/20260905 and baseline-hybrid / hybrid-baseline /
baseline-hybrid ordering. Repeats reuse cases and are not independent samples.

All English model work uses DeepAgent 0.7.12 and langchain-ollama 1.1.0 with
local Ollama 0.33.0 `qwen3:14b`, full digest
`bdbd181c33f2ed1b31c972991882db3cf4d192569092138a7d29e973cd9debe8`.
Temperature zero; thinking/streaming false; context 16,384; output cap128;
two case workers and two Ollama slots; Flash Attention1; q8_0 KV cache;
one loaded model; keep-alive -1. Main inference seed is 20260902.

Preserve exact argv, logs, checkpoints, traces, token counts, timings, errors,
source and package hashes, frozen fingerprints, comparisons and decisions.
Package safe evidence without licensed source text. Audit the manifest, case
arithmetic, data freshness, model work and statistical calculations before
generating the required LEDGAR-only report with paper-ready methods/results,
repeatability and limitations. Run the repository verifier and report audit.
Do not replace the three-dataset manuscript during this LEDGAR-only phase.

The evidence concerns fixed English versus hybrid classification execution.
Construction provenance does not establish autonomous rule-discovery reliability.
Do not claim full-workflow or production effectiveness, dollar/energy savings,
or reduced output variability without supporting measurements. Stop after the
valid LEDGAR evidence package and report; no other dataset is authorized now.
