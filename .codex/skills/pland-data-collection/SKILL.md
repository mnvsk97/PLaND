---
name: pland-data-collection
description: Run, resume, audit, and package PLaND paper experiments from a user-reviewed frozen plan. Use when asked to start or continue data collection, execute evaluation runs, open a gated final test, or turn new runs into paper evidence.
---

# PLaND Data Collection

This is an operations skill, not a third PLaND methodology stage. It coordinates
`generate-initial-version` and `pland-evolver` while preserving a reviewable
evidence chain.

## Current paper collection boundary

The fresh LEDGAR, CFPB, and SpamAssassin collection uses exactly **500
development / 1,000 selection / 500 final-test** cases per dataset. Reject a
plan with different split sizes. Do not copy the historical PDF's
100/100/1,000 sizes into the new collection.

Keep the PDF's scientific claim scope: evaluate fixed English and hybrid SOP
execution, selective Python work with model fallback, classification quality,
model calls, and model tokens. Record how Codex and the two skills constructed
the packages for provenance, but do not present one construction run as an
independent evaluation of autonomous rule-discovery reliability. Do not expand
the results into claims about full business workflows, production deployment,
lower output variability, dollar savings, or energy savings.

## Before any model or dataset work

1. Identify the exact experiment-plan file the user reviewed. Read it in full.
   Do not select an agent-generated draft merely because it exists. If the
   reviewed plan cannot be identified, stop and ask for that decision.
2. Read [the evidence contract](references/evidence-contract.md).
3. Run the controller's `init` command. For paper evidence, require a clean Git
   tree; do not use `--allow-dirty` merely to bypass the check.
4. Run preflights through the controller so the exact command, inputs, output,
   logs, exit status, and hashes enter the ledger.

The user's request to “start data collection” is execution authorization for
the already-reviewed plan. Do not create an additional approval field or
protocol version.

## Collection sequence

Use `scripts/run_collection.py` for every command that creates experimental
evidence. Its gates enforce this order:

1. Prepare and freeze all declared datasets; complete `prepare`.
2. Measure the English baseline on development. Use
   `generate-initial-version` for bounded English-only refinement. Record each
   attempt, then record `ready`, `refine`, or `nonviable` with its decision file.
3. After `ready`, use `pland-evolver` to construct only the number of candidates
   permitted by the plan. Record every candidate development decision. Under
   an explicitly approved multi-attempt plan, use `refine` for an unsuccessful
   attempt with budget remaining, and `nonviable` when exhausted. Stop at the
   first `ready` candidate and freeze it before selection. Never generate
   another candidate after selection has opened.
4. Run paired baseline/candidate selection on identical cases. Record `accept`
   or `reject` from the deterministic assessment artifact.
5. Run final test only after the controller accepts the selection decision.
   Never use final-test observations to revise a baseline or candidate.
6. Package evidence, generate the manifest, then follow
   [paper integration](references/paper-integration.md).
7. Generate the reader-facing report from
   [the final report template](references/final-report-template.md). Populate
   every placeholder from audited artifacts; use `not reached` or `unopened`
   for stages that did not run rather than inventing a value.

Stop a dataset when the plan's attempt limit is reached, the baseline is
nonviable, the candidate is rejected, or selection rejects it. Preserve the
terminal evidence; do not manufacture a replacement candidate.

For an explicit author-approved amendment, retain the original plan and
protocol bytes and hashes, record the amendment and its effective command
boundary in the operations history, and freeze new plan files. Never silently
rewrite an initialized plan or apply an amendment to already opened held-out
evidence.

## Controller

Initialize and inspect a collection:

```bash
python .codex/skills/pland-data-collection/scripts/run_collection.py init \
  --plan PATH_TO_REVIEWED_PLAN --run-dir PATH_TO_NEW_RUN_DIRECTORY
python .codex/skills/pland-data-collection/scripts/run_collection.py status \
  --run-dir PATH_TO_RUN_DIRECTORY
```

Execute commands as argument arrays, never shell strings:

```bash
python .codex/skills/pland-data-collection/scripts/run_collection.py run-command \
  --run-dir PATH_TO_RUN_DIRECTORY --stage prepare --name prepare-datasets \
  --input INPUT_PATH --output OUTPUT_PATH -- COMMAND ARGUMENTS
```

Record gates only from an existing evidence file:

```bash
python .codex/skills/pland-data-collection/scripts/run_collection.py decision \
  --run-dir PATH_TO_RUN_DIRECTORY --stage selection --value accept \
  --evidence PATH_TO_ASSESSMENT_JSON
```

Use `complete-stage` for non-decision stages and `manifest` after packaging.
The controller is resumable: repeating a completed command name verifies its
recorded outputs and skips it; failed commands remain in the ledger and may be
retried without erasing the failure.

## Completion report

Report completed, rejected, failed, and unopened stages separately. State the
dataset, split, case count, frozen model identity, plan hash, SOP/package
hashes, and evidence-manifest path. For a local model, include its full digest;
for a hosted model, include provider, endpoint, and configuration hash without
mislabeling that hash as model weights. Do not call collection paper-ready
until the repository verifier and paper audit both pass against the new evidence.
